import sqlite3
import sqlite_vec
from sentence_transformers import SentenceTransformer
import time
import sys

DB_PATH = "lemma_master.db"
BATCH_SIZE = 10000

print("1. モデルを展開中...（intfloat/multilingual-e5-small）")
model = SentenceTransformer('intfloat/multilingual-e5-small')

db = sqlite3.connect(DB_PATH)
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

# 全件数の事前カウント (進捗計算用)
total_count = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
processed_count = db.execute("SELECT COUNT(*) FROM vec_books").fetchone()[0]

print(f"2. 全件数: {total_count} / 処理済み: {processed_count}")
print(f"   残り約 {total_count - processed_count} 件のベクトル化を開始します。")

loop_count = 0
start_time_total = time.time()

while True:
    loop_start = time.time()
    
    # 未処理データの抽出 (LEFT JOINを用いて高速かつ安全に抽出)
    cursor = db.execute(f'''
        SELECT b.rowid, b.title, b.author, b.publisher 
        FROM books b
        LEFT JOIN vec_books v ON b.rowid = v.id
        WHERE v.id IS NULL
        LIMIT {BATCH_SIZE}
    ''')
    rows = cursor.fetchall()

    if not rows:
        print("\n[COMPLETE] すべての書籍のベクトル化が完了しました！")
        break

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
    db.execute("BEGIN TRANSACTION")
    for r_id, emb in zip(row_ids, embeddings):
        db.execute(
            "INSERT INTO vec_books(id, embedding) VALUES (?, ?)",
            (r_id, sqlite_vec.serialize_float32(emb))
        )
    db.commit()

    processed_count += len(rows)
    loop_time = time.time() - loop_start
    speed = len(rows) / loop_time
    
    # ターミナルでの進捗上書き表示
    sys.stdout.write(f"\r進捗: {processed_count}/{total_count} ({processed_count/total_count*100:.2f}%) | 速度: {speed:.1f}件/秒 | 最終バッチ: {loop_time:.2f}秒")
    sys.stdout.flush()
    
    loop_count += 1

total_elapsed = time.time() - start_time_total
print(f"\n全バッチ処理が終了しました。総稼働時間: {total_elapsed/60:.2f} 分")
db.close()
