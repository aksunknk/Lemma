"""
Lemma API — 4D Vector Book Search Engine
物理PC上の .db ファイル群を直接展開し、120万件の書籍空間から
最近傍ベクトルを抽出するFastAPIサーバー。
"""

import datetime
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from vector_search import LemmaSearchEngine
from nlp_processor import QueryVectorizer

# --- ロギング ---
logger = logging.getLogger("lemma")

# --- 定数 ---
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

# --- CORS 許可オリジン ---
ALLOWED_ORIGINS = [
    "https://node4d.xyz",
    "https://api.node4d.xyz",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
]

# --- アプリケーション初期化 ---
app = FastAPI(title="Lemma API", description="4D Vector Book Search Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = LemmaSearchEngine()
logger.info("Search engine initialized with %d records.", len(engine.df))


# --- リクエスト / レスポンス モデル ---
class SearchPayload(BaseModel):
    query: Optional[str] = None
    era_min: Optional[float] = None
    era_max: Optional[float] = None
    origin: Optional[float] = None
    style: Optional[float] = None
    renown: Optional[float] = None
    keyword: Optional[str] = None


class SearchResult(BaseModel):
    status: int
    item_id: str
    title: str
    author: str
    source: str
    category: str
    distance: float
    vector: list[float]


# --- ルーティング ---
@app.post("/api/search")
async def search_book(req: SearchPayload):
    try:
        era_min = req.era_min if req.era_min is not None else 0.0
        era_max = req.era_max if req.era_max is not None else 1.0
        origin = req.origin if req.origin is not None else 0.5
        style = req.style if req.style is not None else 0.5
        renown = req.renown if req.renown is not None else 0.5
        keyword = req.keyword

        # 自然言語クエリの処理
        if req.query:
            v, category, extracted_keyword = QueryVectorizer.vectorize(req.query)
            era_mid = v[0]
            era_min = max(0.0, era_mid - NLP_ERA_MARGIN)
            era_max = min(1.0, era_mid + NLP_ERA_MARGIN)
            origin, style, renown = v[1], v[2], v[3]
            if extracted_keyword:
                keyword = extracted_keyword

        # イースターエッグ: 2030年モード
        if keyword == "2030" or (
            era_min >= EASTER_EGG_THRESHOLD and era_max >= EASTER_EGG_THRESHOLD
        ):
            title = FUTURE_MAGAZINES.get(
                datetime.datetime.now().weekday(), "謎の未来週刊誌"
            )
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

        target_vector = [(era_min + era_max) / 2.0, origin, style, renown]

        result = engine.search_closest_book(
            target_vector,
            threshold=0.3,
            era_min=era_min,
            era_max=era_max,
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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
