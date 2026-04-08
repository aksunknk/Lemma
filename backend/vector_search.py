import sqlite3
import numpy as np
import pandas as pd
import json
import sys
import random
import os

class LemmaSearchEngine:
    def __init__(self, db_path="lemma_master.db", manga_db_path="lemma_manga.db", new_books_db_path="lemma_new_books.db"):
        self.db_path = db_path
        self.manga_db_path = manga_db_path
        self.new_books_db_path = new_books_db_path
        self._load_data()

    def _load_data(self):
        # メインDB（lemma_master.db）に接続
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 各種DBをアタッチして単一クエリ空間化
        if os.path.exists(self.manga_db_path):
            cursor.execute(f"ATTACH DATABASE '{self.manga_db_path}' AS manga_db")
        if os.path.exists(self.new_books_db_path):
            cursor.execute(f"ATTACH DATABASE '{self.new_books_db_path}' AS new_books")
            
        # 仮想統合空間の構築（UNION ALL）
        queries = []
        # Main Books
        queries.append("""
            SELECT isbn as item_id, title, author, publisher as source, 
                   era, origin, style, renown, 'book' as category FROM books
        """)
        # Manga
        if os.path.exists(self.manga_db_path):
            queries.append("""
                SELECT CAST(id AS TEXT) as item_id, title, author, source, 
                       era, origin, style, renown, 'manga' as category FROM manga_db.manga
            """)
        # New Books (2024-2026)
        if os.path.exists(self.new_books_db_path):
            queries.append("""
                SELECT isbn as item_id, title, author, publisher as source, 
                       era, origin, style, renown, category FROM new_books.books
            """)
            
        query = " UNION ALL ".join(queries)
        
        self.df = pd.read_sql_query(query, conn)
        conn.close()
        
        # NaN パージ（ベクトル成分が欠落しているレコードを排除）
        self.df = self.df.dropna(subset=['era', 'origin', 'style', 'renown'])
        
        # ベクトル行列の生成
        self.vectors = self.df[['era', 'origin', 'style', 'renown']].values

    def search_closest_book(self, target_vector, threshold=0.3, era_min=0.0, era_max=1.0, keyword=None):
        if len(target_vector) != 4:
            raise ValueError("Vector must be exactly 4 dimensions.")

        # 事前フィルタリング (年代範囲による足切り)
        mask = (self.df['era'] >= era_min) & (self.df['era'] <= era_max)
        
        # ORIGIN（属性）の絶対防壁化
        target_origin = target_vector[1]
        if target_origin <= 0.1: # 国内指定 (0.0近辺)
            mask = mask & (self.df['origin'] < 0.5)
        elif target_origin >= 0.9: # 海外指定 (1.0近辺)
            mask = mask & (self.df['origin'] >= 0.5)

        # キーワードによる絞り込み
        if keyword:
            keyword = keyword.lower()
            mask = mask & (
                self.df['title'].str.lower().str.contains(keyword, na=False, regex=False) | 
                self.df['author'].str.lower().str.contains(keyword, na=False, regex=False)
            )

        filtered_df = self.df[mask]
        
        if filtered_df.empty:
            return {
                "status": 404,
                "message": f"「誠実な沈黙」: 指定された条件に該当する作品がこの空間には存在しません。",
                "min_distance": None
            }

        filtered_vectors = filtered_df[['era', 'origin', 'style', 'renown']].values
        target = np.array(target_vector)
        distances = np.linalg.norm(filtered_vectors - target, axis=1)
        
        # ソート
        sorted_indices = np.argsort(distances)

        # 閾値内の Top 5 候補
        top_k = 5
        candidates = []
        for idx in sorted_indices[:top_k]:
            if distances[idx] <= threshold:
                candidates.append(idx)

        # 閾値外の場合
        if not candidates:
            min_dist = distances[sorted_indices[0]]
            return {
                "status": 404,
                "message": f"誠実な沈黙: 条件に合致する作品が存在しません。(最小距離: {round(float(min_dist), 4)})",
                "min_distance": round(float(min_dist), 4)
            }

        # 候補からランダム抽出 (ゆらぎ)
        picked_idx = int(random.choice(candidates))
        picked_dist = float(distances[picked_idx])
        best_item = filtered_df.iloc[picked_idx]

        return {
            "status": 200,
            "item_id": str(best_item['item_id']),
            "title": str(best_item['title']),
            "author": str(best_item['author']),
            "source": str(best_item['source']),
            "category": str(best_item['category']),
            "distance": round(picked_dist, 4),
            "vector": [
                float(best_item['era']), 
                float(best_item['origin']), 
                float(best_item['style']), 
                float(best_item['renown'])
            ]
        }

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    engine = LemmaSearchEngine()
    print(f"=== Unified Search Engine Core Test (Total Records: {len(engine.df)}) ===")
    
    # テストクエリ: 近代国内・高知名度（マンガと活字が混在する領域）
    test_vec = [0.8, 0.0, 0.5, 0.8]
    print(f"\nTarget Vector {test_vec} ->")
    print(json.dumps(engine.search_closest_book(test_vec), indent=2, ensure_ascii=False))
