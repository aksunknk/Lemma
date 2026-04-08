import sqlite3
from tqdm import tqdm

SOURCE_DB = "new_books_2024_2026.db"
TARGET_DB = "lemma_new_books.db"

def get_style(publisher):
    academic = ["岩波書店", "筑摩書房", "平凡社", "みすず書房", "東京大学出版会"]
    return 0.8 if any(a in publisher for a in academic) else 0.5

def get_renown(publisher):
    major = ["講談社", "集英社", "KADOKAWA", "小学館", "文藝春秋", "新潮社"]
    return 0.9 if any(m in publisher for m in major) else 0.5

def bulk_vectorize():
    # ソース接続
    s_conn = sqlite3.connect(SOURCE_DB)
    s_cursor = s_conn.cursor()
    
    # ターゲット接続・スキーマ構築
    t_conn = sqlite3.connect(TARGET_DB)
    t_cursor = t_conn.cursor()
    t_cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            isbn TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            publisher TEXT,
            era REAL,
            origin REAL,
            style REAL,
            renown REAL,
            category TEXT
        )
    """)
    
    # データ読み込み
    s_cursor.execute("SELECT isbn, title, author, publisher FROM cleaned_books")
    rows = s_cursor.fetchall()
    total = len(rows)
    
    batch_size = 1000
    batch_data = []
    
    for row in tqdm(rows, desc="Vectorizing"):
        isbn, title, author, publisher = row
        
        era = 1.0
        origin = 0.0
        style = get_style(publisher)
        renown = get_renown(publisher)
        category = "book"
        
        batch_data.append((isbn, title, author, publisher, era, origin, style, renown, category))
        
        if len(batch_data) >= batch_size:
            t_cursor.executemany("INSERT OR IGNORE INTO books VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", batch_data)
            t_conn.commit()
            batch_data = []
            
    if batch_data:
        t_cursor.executemany("INSERT OR IGNORE INTO books VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", batch_data)
        t_conn.commit()
        
    s_conn.close()
    t_conn.close()
    print(f"\nMigration Complete: {total} records vectorized and saved to {TARGET_DB}.")

if __name__ == "__main__":
    bulk_vectorize()
