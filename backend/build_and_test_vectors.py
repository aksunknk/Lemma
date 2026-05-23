import sqlite3
import sqlite_vec
from sentence_transformers import SentenceTransformer
import time

DB_PATH = "lemma_master.db"
BATCH_SIZE = 5000

print("1. モデルをメモリに展開中...（intfloat/multilingual-e5-small）")
model = SentenceTransformer('intfloat/multilingual-e5-small')

print("2. データベース接続および sqlite-vec のロード...")
db = sqlite3.connect(DB_PATH)
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

# ベクトル用仮想テーブルの作成
db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vec_books USING vec0(id INTEGER PRIMARY KEY, embedding float[384])")

# 未処理のレコードを取得（最初の5000件）
cursor = db.execute('''
    SELECT rowid, title, author, publisher 
    FROM books 
    WHERE rowid NOT IN (SELECT id FROM vec_books)
    LIMIT ?
''', (BATCH_SIZE,))
rows = cursor.fetchall()

if not rows:
    print("処理対象の未ベクトル化データが存在しません。")
    db.close()
    exit(0)

print(f"3. {len(rows)} 件の書籍データのベクトル化を開始します...")
start_time = time.time()

texts = []
row_ids = []
for row in rows:
    r_id, title, author, publisher = row
    t = title if title else "不明"
    a = author if author else "不明"
    p = publisher if publisher else "不明"
    texts.append(f"タイトル: {t} 著者: {a} 出版社: {p}")
    row_ids.append(r_id)

# 一括エンコード
embeddings = model.encode(texts, show_progress_bar=False)

# データベースへの書き込み
print("4. ベクトル空間への書き込みを実行中...")
db.execute("BEGIN TRANSACTION")
for r_id, emb in zip(row_ids, embeddings):
    db.execute(
        "INSERT INTO vec_books(id, embedding) VALUES (?, ?)",
        (r_id, sqlite_vec.serialize_float32(emb))
    )
db.commit()

elapsed_time = time.time() - start_time
print(f"   [OK] 5000件の書き込みが完了しました（所要時間: {elapsed_time:.2f}秒）")

# --- その場でのKNN検索テスト ---
print("\n5. --- 観測結果：実データに対するKNN検索テスト ---")
query_text = "インフラ構築やDockerに関する硬派な技術書"
print(f"検証クエリ: '{query_text}'")
query_vec = model.encode([query_text])[0]

# 実際に挿入した5000件の中から、クエリに近い上位3件を抽出
# booksテーブルとJOINして詳細情報を取得
results = db.execute(
    """
    SELECT v.id, v.distance, b.title, b.author, b.publisher
    FROM (
        SELECT id, distance
        FROM vec_books
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT 3
    ) v
    JOIN books b ON v.id = b.rowid
    """,
    (sqlite_vec.serialize_float32(query_vec),)
).fetchall()

for rank, row in enumerate(results, 1):
    b_id, distance, title, author, publisher = row
    print(f"  {rank}位 (距離: {distance:.4f}) -> ID:{b_id} | タイトル: {title} | 著者: {author} | 出版社: {publisher}")

db.close()
