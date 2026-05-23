"""
Lemma Search Engine — Stateless Hybrid Vector Search
sqlite-vecによる384次元ベクトル検索とメタデータフィルタリングを併用し、
メモリを消費しない完全ステートレスな最近傍探索を行う。
"""
import sqlite3
import random
import logging
import sqlite_vec
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("lemma.engine")

DEFAULT_TOP_K = 5
ORIGIN_DOMESTIC_CEILING = 0.1
ORIGIN_FOREIGN_FLOOR = 0.9

class LemmaSearchEngine:
    """メモリにデータを保持せず、オンデマンドでSQLite空間を探索するエンジン。"""
    def __init__(self, db_path: str = "lemma_master.db"):
        self.db_path = db_path
        logger.info("Initializing SentenceTransformer (e5-small)...")
        # 起動時に軽量モデルのみをメモリに展開（データ自体は保持しない）
        self.model = SentenceTransformer('intfloat/multilingual-e5-small')
        logger.info("Stateless Search Engine initialized.")

    def _get_connection(self) -> sqlite3.Connection:
        """リクエストのたびに軽量な接続を生成し、sqlite-vecをロードする"""
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn

    def search_closest_book(
        self,
        query_text: str = None,
        era_min: float = 0.0,
        era_max: float = 1.0,
        target_origin: float = 0.5,
        keyword: str | None = None,
    ) -> dict:
        """ターゲットテキストの384DベクトルとSQLフィルタを用いて書籍を抽出する。"""
        # クエリテキストが存在しない場合（スライダーのみの操作時）のフォールバック
        search_text = query_text if query_text else "おすすめの面白い本"
        query_vec = self.model.encode([search_text])[0]

        with self._get_connection() as conn:
            params = [sqlite_vec.serialize_float32(query_vec), era_min, era_max]
            
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

            # ハイブリッド検索クエリ (KNN検索結果をサブクエリで取得し、JOINでフィルタリング)
            sql = f"""
            SELECT b.rowid, b.title, b.author, b.publisher, 'book' as category, 
                   b.era, b.origin, b.style, b.renown, v.distance
            FROM (
                SELECT id, distance FROM vec_books
                WHERE embedding MATCH ? AND k = 250
            ) v
            JOIN books b ON v.id = b.rowid
            WHERE b.era BETWEEN ? AND ?
              {origin_condition}
              {keyword_condition}
            ORDER BY v.distance
            LIMIT {DEFAULT_TOP_K}
            """

            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

            if not rows:
                return {
                    "status": 404,
                    "message": "「誠実な沈黙」: 指定された条件に該当する作品がこの空間には存在しません。",
                    "min_distance": None,
                }

            # 候補からランダム抽出 (ゆらぎ)
            best_item = random.choice(rows)
            
            return {
                "status": 200,
                "item_id": str(best_item[0]),
                "title": str(best_item[1] if best_item[1] else "不明"),
                "author": str(best_item[2] if best_item[2] else "不明"),
                "source": str(best_item[3] if best_item[3] else "不明"),
                "category": str(best_item[4]),
                "distance": round(best_item[9], 4),
                "vector": [
                    float(best_item[5] if best_item[5] is not None else 0.5),
                    float(best_item[6] if best_item[6] is not None else 0.5),
                    float(best_item[7] if best_item[7] is not None else 0.5),
                    float(best_item[8] if best_item[8] is not None else 0.5),
                ],
            }
