"""
Lemma Search Engine — 4D Vector Space Nearest-Neighbor Search
複数のSQLiteデータベースを仮想統合空間として結合し、
4次元ベクトル (ERA, ORIGIN, STYLE, RENOWN) による最近傍探索を行う。
"""
import sqlite3
import random
import os
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("lemma.engine")

# --- 定数 ---
VECTOR_DIMENSIONS = 4
VECTOR_COLUMNS = ["era", "origin", "style", "renown"]
DEFAULT_TOP_K = 5
DEFAULT_THRESHOLD = 0.3
ORIGIN_DOMESTIC_CEILING = 0.1
ORIGIN_FOREIGN_FLOOR = 0.9


class LemmaSearchEngine:
    """120万件の書籍レコードをメモリ上に展開し、ベクトル空間探索を行うエンジン。"""

    def __init__(
        self,
        db_path: str = "lemma_master.db",
        manga_db_path: str = "lemma_manga.db",
        new_books_db_path: str = "lemma_new_books.db",
    ):
        self.db_path = db_path
        self.manga_db_path = manga_db_path
        self.new_books_db_path = new_books_db_path
        self._load_data()

    def _load_data(self) -> None:
        """全DBを統合し、ベクトル行列としてメモリに展開する。"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 各種DBをアタッチして単一クエリ空間化
            if os.path.exists(self.manga_db_path):
                cursor.execute("ATTACH DATABASE ? AS manga_db", (self.manga_db_path,))
            if os.path.exists(self.new_books_db_path):
                cursor.execute("ATTACH DATABASE ? AS new_books", (self.new_books_db_path,))

            # 仮想統合空間の構築（UNION ALL）
            queries = [
                """SELECT isbn as item_id, title, author, publisher as source,
                          era, origin, style, renown, 'book' as category FROM books"""
            ]
            if os.path.exists(self.manga_db_path):
                queries.append(
                    """SELECT CAST(id AS TEXT) as item_id, title, author, source,
                              era, origin, style, renown, 'manga' as category FROM manga_db.manga"""
                )
            if os.path.exists(self.new_books_db_path):
                queries.append(
                    """SELECT isbn as item_id, title, author, publisher as source,
                              era, origin, style, renown, category FROM new_books.books"""
                )

            unified_query = " UNION ALL ".join(queries)
            self.df = pd.read_sql_query(unified_query, conn)

        # NaN パージ（ベクトル成分が欠落しているレコードを排除）
        self.df = self.df.dropna(subset=VECTOR_COLUMNS)

        # ベクトル行列の生成
        self.vectors = self.df[VECTOR_COLUMNS].values

        logger.info("Loaded %d records into vector space.", len(self.df))

    def search_closest_book(
        self,
        target_vector: list[float],
        threshold: float = DEFAULT_THRESHOLD,
        era_min: float = 0.0,
        era_max: float = 1.0,
        keyword: str | None = None,
    ) -> dict:
        """ターゲットベクトルに最も近い書籍を抽出する。"""
        if len(target_vector) != VECTOR_DIMENSIONS:
            raise ValueError(f"Vector must be exactly {VECTOR_DIMENSIONS} dimensions.")

        # 事前フィルタリング (年代範囲による足切り)
        mask = (self.df["era"] >= era_min) & (self.df["era"] <= era_max)

        # ORIGIN（属性）の絶対防壁化
        target_origin = target_vector[1]
        if target_origin <= ORIGIN_DOMESTIC_CEILING:
            mask = mask & (self.df["origin"] < 0.5)
        elif target_origin >= ORIGIN_FOREIGN_FLOOR:
            mask = mask & (self.df["origin"] >= 0.5)

        # キーワードによる絞り込み
        if keyword:
            keyword_lower = keyword.lower()
            mask = mask & (
                self.df["title"].str.lower().str.contains(keyword_lower, na=False, regex=False)
                | self.df["author"].str.lower().str.contains(keyword_lower, na=False, regex=False)
            )

        filtered_df = self.df[mask]

        if filtered_df.empty:
            return {
                "status": 404,
                "message": "「誠実な沈黙」: 指定された条件に該当する作品がこの空間には存在しません。",
                "min_distance": None,
            }

        # ユークリッド距離の計算
        filtered_vectors = filtered_df[VECTOR_COLUMNS].values
        target = np.array(target_vector)
        distances = np.linalg.norm(filtered_vectors - target, axis=1)

        sorted_indices = np.argsort(distances)

        # 閾値内の Top-K 候補
        candidates = [idx for idx in sorted_indices[:DEFAULT_TOP_K] if distances[idx] <= threshold]

        if not candidates:
            min_dist = float(distances[sorted_indices[0]])
            return {
                "status": 404,
                "message": f"誠実な沈黙: 条件に合致する作品が存在しません。(最小距離: {round(min_dist, 4)})",
                "min_distance": round(min_dist, 4),
            }

        # 候補からランダム抽出 (ゆらぎ)
        picked_idx = int(random.choice(candidates))
        picked_dist = float(distances[picked_idx])
        best_item = filtered_df.iloc[picked_idx]

        return {
            "status": 200,
            "item_id": str(best_item["item_id"]),
            "title": str(best_item["title"]),
            "author": str(best_item["author"]),
            "source": str(best_item["source"]),
            "category": str(best_item["category"]),
            "distance": round(picked_dist, 4),
            "vector": [
                float(best_item["era"]),
                float(best_item["origin"]),
                float(best_item["style"]),
                float(best_item["renown"]),
            ],
        }


if __name__ == "__main__":
    import sys
    import json

    sys.stdout.reconfigure(encoding="utf-8")
    search_engine = LemmaSearchEngine()
    print(f"=== Unified Search Engine Core Test (Total Records: {len(search_engine.df)}) ===")

    test_vec = [0.8, 0.0, 0.5, 0.8]
    print(f"\nTarget Vector {test_vec} ->")
    print(json.dumps(search_engine.search_closest_book(test_vec), indent=2, ensure_ascii=False))
