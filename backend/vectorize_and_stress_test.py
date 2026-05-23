import sqlite3
import sqlite_vec
from sentence_transformers import SentenceTransformer
import os
import time
import random

print("1. SentenceTransformerモデルを展開中...")
model = SentenceTransformer('intfloat/multilingual-e5-small')

def process_db(db_path, table_name, publisher_col):
    if not os.path.exists(db_path):
        print(f"[SKIP] {db_path} が見つかりません。")
        return

    db = sqlite3.connect(db_path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    vec_table = f"vec_{table_name}"
    db.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {vec_table} USING vec0(id INTEGER PRIMARY KEY, embedding float[384])")

    cursor = db.execute(f'''
        SELECT b.rowid, b.title, b.author, b.{publisher_col} 
        FROM {table_name} b
        LEFT JOIN {vec_table} v ON b.rowid = v.id
        WHERE v.id IS NULL
    ''')
    rows = cursor.fetchall()

    if rows:
        print(f"[{db_path}] {len(rows)}件のベクトル化を開始...")
        texts = [f"タイトル: {r[1] or '不明'} 著者: {r[2] or '不明'} 出版社: {r[3] or '不明'}" for r in rows]
        embeddings = model.encode(texts, show_progress_bar=False)
        
        db.execute("BEGIN TRANSACTION")
        for r_id, emb in zip([r[0] for r in rows], embeddings):
            db.execute(
                f"INSERT INTO {vec_table}(id, embedding) VALUES (?, ?)",
                (r_id, sqlite_vec.serialize_float32(emb))
            )
        db.commit()
        print(f"[{db_path}] ベクトル化完了。")
    else:
        print(f"[{db_path}] 既にベクトル化済みです。")
    db.close()

# 1. サブDBのベクトル化実行
process_db("lemma_manga.db", "manga", "source")
process_db("lemma_new_books.db", "books", "publisher")

# 2. 100件のテストケース自動生成
print("\n2. 100件のテストケースを自動生成中...")
topics = ["サイバーパンク", "魔法少女", "異世界転生", "ハードボイルド", "哲学的なSF", "日常系のコメディ", "本格ミステリー", "中世ヨーロッパ風のファンタジー", "ディストピア", "青春恋愛"]
test_cases = []
for _ in range(100):
    query = f"{random.choice(topics)}の面白い作品"
    era_min, era_max = sorted([random.random(), random.random()])
    origin = random.random()
    test_cases.append({"query": query, "era_min": era_min, "era_max": era_max, "origin": origin})

# 3. 連続ストレステストの実行
print("3. ストレステスト（100件連続クエリ）を開始...")
total_time = 0
errors = 0
sample_results = []

db = sqlite3.connect("lemma_manga.db")
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

for i, case in enumerate(test_cases):
    start_time = time.time()
    query_vec = model.encode([case["query"]])[0]
    
    try:
        # Manga DBに対してKNN検索を実行
        cursor = db.execute("""
            SELECT b.title, v.distance 
            FROM vec_manga v
            JOIN manga b ON v.id = b.rowid
            WHERE v.embedding MATCH ? AND k = 5
            ORDER BY v.distance LIMIT 1
        """, (sqlite_vec.serialize_float32(query_vec),))
        result = cursor.fetchone()
        elapsed = time.time() - start_time
        total_time += elapsed

        if i % 33 == 0 and result:  # サンプルとして約3件抽出
            sample_results.append(f"Q: '{case['query']}' -> A: {result[0]} (距離: {result[1]:.4f})")
            
    except Exception as e:
        errors += 1

db.close()

# 4. 観測結果の出力
avg_time = total_time / 100
print("\n--- 観測結果：100件ストレステスト ---")
print(f"総実行時間: {total_time:.2f} 秒")
print(f"平均レイテンシ: {avg_time*1000:.2f} ms / クエリ")
print(f"エラー数: {errors} 件")
print("\n[抽出サンプル]")
for res in sample_results:
    print(res)
