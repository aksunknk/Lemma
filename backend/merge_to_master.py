import sqlite3
import os

MASTER_DB = "lemma_master.db"
SOURCE_DBS = [
    "openbd_supplement.db",
    "google_raw.db",
    "openbd_raw.db",
    "books.db",
    "rakuten_raw.db"
]

def merge():
    # 既存のマスターがあれば削除（クリーンビルド）
    if os.path.exists(MASTER_DB):
        os.remove(MASTER_DB)

    conn_master = sqlite3.connect(MASTER_DB)
    cursor_master = conn_master.cursor()

    # 1. テーブル作成
    cursor_master.execute("""
        CREATE TABLE books (
            isbn TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            publisher TEXT,
            pubdate TEXT,
            description TEXT,
            era REAL,
            origin REAL,
            style REAL,
            renown REAL
        )
    """)
    conn_master.commit()

    # 2. 各DBの統合
    for db_name in SOURCE_DBS:
        if not os.path.exists(db_name):
            print(f"Skipping {db_name} (not found)")
            continue

        print(f"Merging {db_name}...")
        try:
            conn_src = sqlite3.connect(f"file:{db_name}?mode=ro", uri=True)
            cursor_src = conn_src.cursor()
            
            # 全データをフェッチして挿入
            cursor_src.execute("SELECT isbn, title, author, publisher, pubdate, description, era, origin, style, renown FROM books")
            rows = cursor_src.fetchall()
            
            cursor_master.executemany("""
                INSERT OR IGNORE INTO books 
                (isbn, title, author, publisher, pubdate, description, era, origin, style, renown)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            
            print(f"  -> Processed {len(rows):,} records from {db_name}")
            conn_src.close()
            conn_master.commit()
        except Exception as e:
            print(f"  -> Error merging {db_name}: {e}")

    # 3. インデックス作成
    print("Creating indexes on vector columns...")
    cursor_master.execute("CREATE INDEX idx_era ON books(era)")
    cursor_master.execute("CREATE INDEX idx_origin ON books(origin)")
    cursor_master.execute("CREATE INDEX idx_style ON books(style)")
    cursor_master.execute("CREATE INDEX idx_renown ON books(renown)")
    conn_master.commit()

    # 4. 最終カウント
    cursor_master.execute("SELECT COUNT(*) FROM books")
    final_total = cursor_master.fetchone()[0]

    # 5. VACUUM
    print("Finalizing (VACUUM)...")
    conn_master.execute("VACUUM")
    conn_master.close()

    print("-" * 50)
    print("=== [lemma] Master Database Integration Complete ===")
    print("-" * 50)
    print(f"Integrated Total Records: {final_total:,}")
    print(f"Master Database Path:    {MASTER_DB}")
    print("-" * 50)

if __name__ == "__main__":
    merge()
