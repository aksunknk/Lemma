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
import math
import datetime
import numpy as np
import sqlite_vec
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

logger = logging.getLogger("lemma.engine")

DEFAULT_BASELINE_WEIGHT = 0.3
DEFAULT_HALF_LIFE_DAYS = 180.0


def calculate_time_decay(
    date_str: str | None,
    baseline_weight: float = DEFAULT_BASELINE_WEIGHT,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """
    各アイテムのウェイト（重み）を計算する。
    - 日付（date）が YYYY-MM-DD 形式で存在する場合:
      現在日付からの経過日数を計算し、半減期を180日とする指数関数的減衰（exp(-lambda * days)）を計算してウェイトとする。
    - 日付が空（null）またはパースエラーの場合:
      過去の遺産として固定のベースライン・ウェイト（0.3）を返す。
    """
    if not date_str or not isinstance(date_str, str) or not date_str.strip():
        return baseline_weight

    date_clean = date_str.strip()
    parsed_date = None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            parsed_date = datetime.datetime.strptime(date_clean[:10], fmt).date()
            break
        except (ValueError, TypeError):
            continue

    if parsed_date is None:
        try:
            parsed_date = datetime.date.fromisoformat(date_clean[:10])
        except (ValueError, TypeError):
            return baseline_weight

    today = datetime.date.today()
    days = (today - parsed_date).days
    if days < 0:
        days = 0

    decay_lambda = math.log(2) / half_life_days
    weight = math.exp(-decay_lambda * days)
    return float(weight)


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
        ORDER BY v.distance
        LIMIT {DEFAULT_TOP_K * 20}
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
            title = str(row[1] if row[1] else "不明")
            author = str(row[2] if row[2] else "不明")
            dist = row[9]
            
            # キーワードボーナスの適用（タイトルまたは著者にキーワードが含まれていれば距離を縮める）
            if keyword and (keyword.lower() in title.lower() or keyword.lower() in author.lower()):
                dist -= 0.15

            results.append({
                "item_id": str(row[0]),
                "title": title,
                "author": author,
                "source": str(row[3] if row[3] else "不明"),
                "category": str(row[4]),
                "distance": dist,
                "vector": [
                    float(row[5] if row[5] is not None else 0.5),
                    float(row[6] if row[6] is not None else 0.5),
                    float(row[7] if row[7] is not None else 0.5),
                    float(row[8] if row[8] is not None else 0.5),
                ],
            })
        return results

    def _search_single_db_fallback(
        self,
        config: dict,
        era_min: float,
        era_max: float,
        target_origin: float,
        keyword: str,
    ) -> list[dict]:
        """KNN結果が空の場合に、直接データベースから部分一致 (LIKE) で候補を検索するフォールバック処理。"""
        db_path = os.path.join(self.db_dir, config["path"])
        if not os.path.exists(db_path):
            return []

        table = config["table"]
        publisher_col = config["publisher_col"]
        category = config["category"]

        # ORIGIN（属性）の絶対防壁化
        origin_condition = ""
        if target_origin <= ORIGIN_DOMESTIC_CEILING:
            origin_condition = "AND b.origin < 0.5"
        elif target_origin >= ORIGIN_FOREIGN_FLOOR:
            origin_condition = "AND b.origin >= 0.5"

        sql = f"""
        SELECT b.rowid, b.title, b.author, b.{publisher_col}, '{category}' as category,
               b.era, b.origin, b.style, b.renown, 1.0 as distance
        FROM {table} b
        WHERE b.era BETWEEN ? AND ?
          {origin_condition}
        LIMIT {DEFAULT_TOP_K * 10}
        """

        params = [era_min, era_max]

        try:
            with self._get_connection(db_path) as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
        except Exception as e:
            logger.error("Fallback search failed on %s: %s", config["path"], e)
            return []

        results = []
        for row in rows:
            title = str(row[1] if row[1] else "不明")
            author = str(row[2] if row[2] else "不明")
            dist = row[9]
            
            if keyword and (keyword.lower() in title.lower() or keyword.lower() in author.lower()):
                dist -= 0.15

            results.append({
                "item_id": str(row[0]),
                "title": title,
                "author": author,
                "source": str(row[3] if row[3] else "不明"),
                "category": str(row[4]),
                "distance": dist,
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
        
        # キーワードが存在する場合はクエリテキストに統合し、ベクトル検索の意味を強める
        if keyword:
            search_text = f"{keyword} {search_text}"

        # e5-smallモデルの仕様に合わせ、アシンメトリック検索用に "query: " プレフィックスを付与
        search_text_prefixed = f"query: {search_text}"
        query_vec = self.model.encode([search_text_prefixed])[0]
        serialized_vec = sqlite_vec.serialize_float32(query_vec)

        # 全DBを横断検索し、候補を統合
        all_candidates = []
        for config in DB_CONFIGS:
            candidates = self._search_single_db(
                config, serialized_vec, era_min, era_max, target_origin, keyword
            )
            all_candidates.extend(candidates)

        # ベクトル検索で候補が得られなかった場合のフォールバック（純粋なメタデータ検索）
        if not all_candidates:
            logger.info("KNN results empty. Falling back to SQL search.")
            for config in DB_CONFIGS:
                candidates = self._search_single_db_fallback(
                    config, era_min, era_max, target_origin, keyword
                )
                all_candidates.extend(candidates)

        if not all_candidates:
            return {
                "status": 404,
                "message": "「誠実な沈黙」: 指定された条件に該当する作品がこの空間には存在しません。",
                "min_distance": None,
            }

        # 全候補をボーナス計算後の距離順に再ソートし、上位K件からランダム抽出（ゆらぎ）
        all_candidates.sort(key=lambda x: x["distance"])
        top_candidates = all_candidates[:DEFAULT_TOP_K]
        best_item = random.choice(top_candidates)
        best_item["status"] = 200
        best_item["distance"] = round(best_item["distance"], 4)

        return best_item

    def extract_centroid(self, items: list[dict] | list[str]) -> list[dict]:
        """
        タイム・ディケイ（時間的減衰）とマルチ・セントロイド（多極重心化）を適用し、
        類似するトップ5件の書籍リストを返す。
        """
        if not items:
            return []

        # 入力形式の正規化（dict, str, または属性持ちオブジェクトを統一）
        normalized_items = []
        for item in items:
            if isinstance(item, str):
                title = item.strip()
                if title:
                    normalized_items.append({"title": title, "date": None})
            elif isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                date_val = item.get("date")
                if title:
                    normalized_items.append({"title": title, "date": date_val})
            elif hasattr(item, "title"):
                title = str(getattr(item, "title", "")).strip()
                date_val = getattr(item, "date", None)
                if title:
                    normalized_items.append({"title": title, "date": date_val})

        if not normalized_items:
            return []

        # 1. タイム・ディケイ計算
        weights = np.array(
            [calculate_time_decay(it["date"]) for it in normalized_items],
            dtype=np.float32,
        )

        # 2. 各アイテムの文字列をベクトル化
        search_texts = [f"query: {it['title']}" for it in normalized_items]
        vectors = np.array(self.model.encode(search_texts), dtype=np.float32)

        # 3. ウェイトを掛け合わせる（スカラー倍）
        weighted_vectors = vectors * weights[:, np.newaxis]

        # 4. アイテム数に応じたクラスタ数 k の決定
        n_items = len(normalized_items)
        if n_items <= 2:
            k = 1
        elif n_items <= 5:
            k = 2
        else:
            k = 3

        # KMeansクラスタリングの実行
        if n_items == 1:
            centroids = weighted_vectors
        else:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
            kmeans.fit(weighted_vectors)
            centroids = kmeans.cluster_centers_

        # 5. 各Centroidベクトルに対して全DBを横断検索
        all_candidates = []
        for centroid in centroids:
            serialized_vec = sqlite_vec.serialize_float32(centroid.astype(np.float32))
            for config in DB_CONFIGS:
                candidates = self._search_single_db(
                    config, serialized_vec, 0.0, 1.0, 0.5, None
                )
                all_candidates.extend(candidates)

        # 6. クラスタ間重複の排除・マージおよび入力タイトルの除外
        lower_input_titles = set(it["title"].lower() for it in normalized_items)
        dedup_candidates = {}
        for c in all_candidates:
            c_title = c.get("title", "").strip()
            c_title_lower = c_title.lower()
            if c_title_lower in lower_input_titles:
                continue

            if c_title_lower not in dedup_candidates or c["distance"] < dedup_candidates[c_title_lower]["distance"]:
                dedup_candidates[c_title_lower] = c

        # 7. 距離昇順でソートし上位5件を返却
        sorted_candidates = sorted(dedup_candidates.values(), key=lambda x: x["distance"])
        top_5 = sorted_candidates[:DEFAULT_TOP_K]

        for c in top_5:
            c["status"] = 200
            c["distance"] = round(c["distance"], 4)

        return top_5

