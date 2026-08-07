"""
Lemma API — Stateless Hybrid Vector Search Engine
"""
import datetime
import json
import logging
import os
import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
import uvicorn
from vector_search import LemmaSearchEngine
from nlp_processor import QueryVectorizer

logger = logging.getLogger("lemma")

EASTER_EGG_THRESHOLD = 0.99
NLP_ERA_MARGIN = 0.1
FUTURE_MAGAZINES = {
    0: "週刊少年ジャンプ",
    1: "週刊プレイボーイ",
    2: "週刊少年マガジン",
    3: "週刊ヤングジャンプ",
    4: "フライデー",
    5: "週刊現代",
    6: "週刊ポスト",
}

LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "")

SYSTEM_PROMPT_MIMI_LEMMA = """
あなたは高度な概念抽出エンジンです。ユーザーの読書メモから、その根底にある抽象的な「概念（Concept）」「テーマ（Theme）」「哲学（Philosophy）」を3〜5個抽出してください。
一般的なジャンル名（例: 小説、ビジネス書）は排除し、より深くメタ的なキーワード（例: 時間の非線形性、自己組織化、実存主義）を生成してください。
出力は以下の厳密なJSON形式のみとし、他のテキストは一切含めないでください。
{ "tags": ["概念A", "概念B", "概念C"] }
"""

ALLOWED_ORIGINS = [
    "*",
]

app = FastAPI(title="Lemma API", description="Stateless Hybrid Book Search Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = LemmaSearchEngine()

class SearchPayload(BaseModel):
    query: Optional[str] = None
    era_min: Optional[float] = None
    era_max: Optional[float] = None
    origin: Optional[float] = None
    style: Optional[float] = None
    renown: Optional[float] = None
    keyword: Optional[str] = None

class CentroidItem(BaseModel):
    title: str
    date: Optional[str] = None

class CentroidPayload(BaseModel):
    items: Optional[list[CentroidItem]] = None
    titles: Optional[list[str]] = None

class ExtractConceptsRequest(BaseModel):
    note: str

class ExtractConceptsResponse(BaseModel):
    tags: list[str]

class SearchResult(BaseModel):
    status: int
    item_id: str
    title: str
    author: str
    source: str
    category: str
    distance: float
    vector: list[float]


PLACEHOLDER_TAGS = {"概念a", "概念b", "概念c", "概念1", "概念2", "概念3", "a", "b", "c", "tag1", "tag2", "tag3"}

def _clean_tags(tags: list[str]) -> list[str]:
    cleaned = []
    for t in tags:
        s = str(t).strip()
        if s and s.lower() not in PLACEHOLDER_TAGS and len(s) > 0:
            cleaned.append(s)
    return cleaned

def _parse_llm_json(raw_text: str) -> list[str]:
    if not raw_text:
        return []
    raw_text = raw_text.strip()
    # 1. Look for ```json ... ``` blocks first (most reliable)
    matches = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
    for m in reversed(matches):
        try:
            data = json.loads(m.strip())
            if isinstance(data, dict) and "tags" in data and isinstance(data["tags"], list):
                res = _clean_tags(data["tags"])
                if res:
                    return res
            if isinstance(data, list):
                res = _clean_tags(data)
                if res:
                    return res
        except Exception:
            pass

    # 2. Direct JSON parsing
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict) and "tags" in data and isinstance(data["tags"], list):
            res = _clean_tags(data["tags"])
            if res:
                return res
        if isinstance(data, list):
            res = _clean_tags(data)
            if res:
                return res
    except Exception:
        pass

    # 3. Find all { "tags": [...] } patterns in text, picking the last one
    obj_matches = re.findall(r"\{[^{}]*\"tags\"[^{}]*\}", raw_text)
    for obj_str in reversed(obj_matches):
        try:
            data = json.loads(obj_str)
            if isinstance(data, dict) and "tags" in data and isinstance(data["tags"], list):
                res = _clean_tags(data["tags"])
                if res:
                    return res
        except Exception:
            pass

    return []


async def _get_lm_studio_model(client: httpx.AsyncClient) -> Optional[str]:
    if LM_STUDIO_MODEL:
        return LM_STUDIO_MODEL
    try:
        models_url = LM_STUDIO_URL.rsplit("/chat/completions", 1)[0] + "/models"
        res = await client.get(models_url)
        if res.status_code == 200:
            data = res.json()
            models = [m.get("id") for m in data.get("data", []) if m.get("id")]
            chat_models = [m for m in models if "embed" not in m.lower()]
            if chat_models:
                return chat_models[0]
            if models:
                return models[0]
    except Exception as e:
        logger.warning("Failed to auto-detect LM Studio model: %s", e)
    return None


async def extract_tags_via_llm(note: str) -> list[str]:
    if not note or not note.strip():
        return []

    timeout = httpx.Timeout(180.0, connect=15.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            model = await _get_lm_studio_model(client)

            payload = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_MIMI_LEMMA.strip()},
                    {"role": "user", "content": note.strip()},
                ],
                "temperature": 0.1,
                "max_tokens": 1200,
            }
            if model:
                payload["model"] = model

            response = await client.post(
                LM_STUDIO_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code != 200:
                logger.warning("LM Studio returned non-200 status: %s %s", response.status_code, response.text)
                return []

            res_data = response.json()
            choices = res_data.get("choices", [])
            if not choices:
                return []

            msg = choices[0].get("message", {})
            content = msg.get("content", "") or ""
            reasoning = msg.get("reasoning_content", "") or ""

            tags = _parse_llm_json(content)
            if not tags and reasoning:
                tags = _parse_llm_json(reasoning)

            return tags
    except Exception as e:
        logger.warning("LM Studio tag extraction failed or unreachable: %s", e)
        return []


@app.post("/api/search")
async def search_book(req: SearchPayload):
    try:
        era_min = req.era_min if req.era_min is not None else 0.0
        era_max = req.era_max if req.era_max is not None else 1.0
        origin = req.origin if req.origin is not None else 0.5
        style = req.style if req.style is not None else 0.5
        renown = req.renown if req.renown is not None else 0.5
        keyword = req.keyword

        if req.query:
            v, category, extracted_keyword = QueryVectorizer.vectorize(req.query)
            era_mid = v[0]
            # クエリに明示的な年代キーワードが含まれている場合のみ年代フィルタを適用し、それ以外は全年代を対象とする
            if era_mid is not None and any(k in req.query for k in ["古典", "明治", "大正", "近代", "昭和", "戦後", "現代", "最近", "新刊"]):
                era_min = max(0.0, era_mid - NLP_ERA_MARGIN)
                era_max = min(1.0, era_mid + NLP_ERA_MARGIN)
            
            # クエリから明示的に判定された属性のみ上書きする（未検出の項目はスライダー値を維持）
            if v[1] is not None:
                origin = v[1]
            if v[2] is not None:
                style = v[2]
            if v[3] is not None:
                renown = v[3]

            # クエリ全文がそのままキーワードとして抽出された場合は、部分一致用のキーワードとしては無視する
            if extracted_keyword and extracted_keyword.lower() != req.query.lower():
                keyword = extracted_keyword

        if keyword == "2030" or (era_min >= EASTER_EGG_THRESHOLD and era_max >= EASTER_EGG_THRESHOLD):
            title = FUTURE_MAGAZINES.get(datetime.datetime.now().weekday(), "謎の未来週刊誌")
            return {
                "status": 200,
                "item_id": "FUTURE-ISSUE",
                "title": f"{title}（2030年最新号）",
                "author": "未来の編集部",
                "source": "Time-Shifted Media",
                "category": "future",
                "distance": 0.0,
                "vector": [1.0, 0.5, 0.5, 1.0],
            }

        # ターゲットベクトルではなく、自然言語クエリと必須フィルタを直接渡す
        result = engine.search_closest_book(
            query_text=req.query,
            era_min=era_min,
            era_max=era_max,
            target_origin=origin,
            keyword=keyword,
        )

        if result["status"] == 404:
            raise HTTPException(status_code=404, detail=result["message"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during search")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/extract_centroid")
async def extract_centroid(req: CentroidPayload):
    items = []
    if req.items:
        items = [{"title": item.title, "date": item.date} for item in req.items if item.title and item.title.strip()]
    elif req.titles:
        items = [{"title": title, "date": None} for title in req.titles if title and title.strip()]

    if not items:
        raise HTTPException(status_code=400, detail="items or titles list cannot be empty")
    try:
        results = engine.extract_centroid(items)
        return results
    except Exception as e:
        logger.exception("Unexpected error during extract_centroid")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/extract_concepts", response_model=ExtractConceptsResponse)
async def extract_concepts(req: ExtractConceptsRequest):
    tags = await extract_tags_via_llm(req.note)
    return ExtractConceptsResponse(tags=tags)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
