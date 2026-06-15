"""
Lemma Search Engine — Stateless Hybrid Vector Search
sqlite-vecによる384次元ベクトル検索とメタデータフィルタリングを併用し、
メモリを消費しない完全ステートレスな最近傍探索を行う。
複数DB（master / new_books / manga）を横断して統合検索する。
"""
import sqlite3
import random
import logging
import os
import sqlite_vec
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("lemma.engine")

DEFAULT_TOP_K = 5
KNN_CANDIDATES = 1000
ORIGIN_DOMESTIC_CEILING = 0.1
ORIGIN_FOREIGN_FLOOR = 0.9

# 検索対象データベース定義
DB_CONFIGS = [
    {
        "path": "lemma_master.db",
        "table": "books",
        "vec_table": "vec_books",
        "publisher_col": "publisher",
        "category": "book",
    },
    {
        "path": "lemma_new_books.db",
        "table": "books",
        "vec_table": "vec_books",
        "publisher_col": "publisher",
        "category": "book",
    },
    {
        "path": "lemma_manga.db",
        "table": "manga",
        "vec_table": "vec_manga",
        "publisher_col": "source",
        "category": "manga",
    },
]


class LemmaSearchEngine:
    """メモリにデータを保持せず、オンデマンドで複数SQLite空間を横断探索するエンジン。"""
    def __init__(self, db_dir: str = "."):
        self.db_dir = db_dir
        logger.info("Initializing SentenceTransformer (e5-small)...")
        # 起動時に軽量モデルのみをメモリに展開（データ自体は保持しない）
        self.model = SentenceTransformer('intfloat/multilingual-e5-small')
        # 各DBの存在を確認しログ出力
        for config in DB_CONFIGS:
            path = os.path.join(self.db_dir, config["path"])
            if os.path.exists(path):
                logger.info("DB registered: %s", config["path"])
            else:
                logger.warning("DB not found: %s (skipped)", config["path"])
        logger.info("Stateless Search Engine initialized (%d DBs).", len(DB_CONFIGS))

    def _get_connection(self, db_path: str) -> sqlite3.Connection:
        """リクエストのたびに軽量な接続を生成し、sqlite-vecをロードする"""
        conn = sqlite3.connect(db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn

    def _search_single_db(
        self,
        config: dict,
        serialized_vec: bytes,
        era_min: float,
        era_max: float,
        target_origin: float,
        keyword: str | None,
    ) -> list[dict]:
        """単一DBに対してKNN検索を実行し、候補リストを返す。"""
        db_path = os.path.join(self.db_dir, config["path"])
        if not os.path.exists(db_path):
            return []

        table = config["table"]
        vec_table = config["vec_table"]
        publisher_col = config["publisher_col"]
        category = config["category"]

        params = [serialized_vec, era_min, era_max]

        # ORIGIN（属性）の絶対防壁化
        origin_condition = ""
        if target_origin <= ORIGIN_DOMESTIC_CEILING:
            origin_condition = "AND b.origin < 0.5"
        elif target_origin >= ORIGIN_FOREIGN_FLOOR:
            origin_condition = "AND b.origin >= 0.5"

        # キーワードによる絞り込み
        keyword_condition = ""
        if keyword:
            keyword_condition = "AND (b.title LIKE ? OR b.author LIKE ?)"
            like_kw = f"%{keyword}%"
            params.extend([like_kw, like_kw])

        sql = f"""
        SELECT b.rowid, b.title, b.author, b.{publisher_col}, '{category}' as category,
               b.era, b.origin, b.style, b.renown, v.distance
        FROM (
            SELECT id, distance FROM {vec_table}
            WHERE embedding MATCH ? AND k = {KNN_CANDIDATES}
        ) v
        JOIN {table} b ON v.id = b.rowid
        WHERE b.era BETWEEN ? AND ?
          {origin_condition}
          {keyword_condition}
        ORDER BY v.distance
        LIMIT {DEFAULT_TOP_K}
        """

        try:
            with self._get_connection(db_path) as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
        except Exception as e:
            logger.error("Search failed on %s: %s", config["path"], e)
            return []

        results = []
        for row in rows:
            results.append({
                "item_id": str(row[0]),
                "title": str(row[1] if row[1] else "不明"),
                "author": str(row[2] if row[2] else "不明"),
                "source": str(row[3] if row[3] else "不明"),
                "category": str(row[4]),
                "distance": row[9],
                "vector": [
                    float(row[5] if row[5] is not None else 0.5),
                    float(row[6] if row[6] is not None else 0.5),
                    float(row[7] if row[7] is not None else 0.5),
                    float(row[8] if row[8] is not None else 0.5),
                ],
            })
        return results

    def search_closest_book(
        self,
        query_text: str = None,
        era_min: float = 0.0,
        era_max: float = 1.0,
        target_origin: float = 0.5,
        keyword: str | None = None,
    ) -> dict:
        """全DBを横断し、384Dベクトルとメタデータフィルタで書籍を抽出する。"""
        # クエリテキストが存在しない場合（スライダーのみの操作時）のフォールバック
        search_text = query_text if query_text else "おすすめの面白い本"
        query_vec = self.model.encode([search_text])[0]
        serialized_vec = sqlite_vec.serialize_float32(query_vec)

        # 全DBを横断検索し、候補を統合
        all_candidates = []
        for config in DB_CONFIGS:
            candidates = self._search_single_db(
                config, serialized_vec, era_min, era_max, target_origin, keyword
            )
            all_candidates.extend(candidates)

        if not all_candidates:
            return {
                "status": 404,
                "message": "「誠実な沈黙」: 指定された条件に該当する作品がこの空間には存在しません。",
                "min_distance": None,
            }

        # 全候補を距離順にソートし、上位K件からランダム抽出（ゆらぎ）
        all_candidates.sort(key=lambda x: x["distance"])
        top_candidates = all_candidates[:DEFAULT_TOP_K]
        best_item = random.choice(top_candidates)
        best_item["status"] = 200
        best_item["distance"] = round(best_item["distance"], 4)

        return best_item
