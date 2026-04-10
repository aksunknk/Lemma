from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from vector_search import LemmaSearchEngine
from nlp_processor import QueryVectorizer
import datetime

app = FastAPI(title="lemma API", description="4D Vector Book Search Engine")

origins = [
    "https://node4d.xyz",
    "https://api.node4d.xyz",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
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

@app.post("/api/search")
async def search_book(req: SearchPayload):
    try:
        # デフォルト値の設定
        era_min = req.era_min if req.era_min is not None else 0.0
        era_max = req.era_max if req.era_max is not None else 1.0
        origin = req.origin if req.origin is not None else 0.5
        style = req.style if req.style is not None else 0.5
        renown = req.renown if req.renown is not None else 0.5
        keyword = req.keyword
        category = None

        # 自然言語クエリの処理
        if req.query:
            v, c, k = QueryVectorizer.vectorize(req.query)
            era_mid = v[0]
            # クエリからの範囲（誤差±0.1）
            era_min = max(0.0, era_mid - 0.1)
            era_max = min(1.0, era_mid + 0.1)
            origin = v[1]
            style = v[2]
            renown = v[3]
            category = c
            if k:
                keyword = k

        # イースターエッグ: 2030年モード
        if keyword == "2030" or (era_min >= 0.99 and era_max >= 0.99):
            today = datetime.datetime.now().weekday()
            magazines = {
                0: "週刊少年ジャンプ", 1: "週刊プレイボーイ", 2: "週刊少年マガジン", 
                3: "週刊ヤングジャンプ", 4: "フライデー", 5: "週刊現代", 6: "週刊ポスト"
            }
            title = magazines.get(today, "謎の未来週刊誌")
            return {
                "status": 200, 
                "item_id": "FUTURE-ISSUE",
                "title": f"{title}（2030年最新号）", 
                "author": "未来の編集部", 
                "source": "Time-Shifted Media",
                "category": "future",
                "distance": 0.0,
                "vector": [1.0, 0.5, 0.5, 1.0]
            }

        target_vector = [(era_min + era_max) / 2.0, origin, style, renown]

        result = engine.search_closest_book(
            target_vector, 
            threshold=0.3,
            era_min=era_min,
            era_max=era_max,
            keyword=keyword
        )
        
        if result["status"] == 404:
            raise HTTPException(status_code=404, detail=result["message"])
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
