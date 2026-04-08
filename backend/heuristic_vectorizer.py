import sqlite3
import re
import random
import time

DB_PATH = "openbd_raw.db"

# キーワード設定
HARD_KEYWORDS = ['論', '考', '研究', '史', '哲学', '社会', '思想', '理不尽', '構造', '経済', '政治', '理論']
SOFT_KEYWORDS = ['異世界', '転生', '魔法', '少女', '恋', 'ちゃん', 'ダンジョン', 'ラブコメ', 'ふあふあ', 'まったり', 'ほのぼの']
MAJOR_PUBLISHERS = ['講談社', '集英社', 'KADOKAWA', '小学館', '文藝春秋', '新潮社', '学研', 'ポプラ社', '岩波書店', '筑摩書房']

def clamp(n, minn=0.0, maxn=1.0):
    return max(min(maxn, n), minn)

def add_columns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 既存のカラムを確認
    cursor.execute("PRAGMA table_info(books)")
    columns = [row[1] for row in cursor.fetchall()]
    
    new_cols = ['era', 'origin', 'style', 'renown']
    for col in new_cols:
        if col not in columns:
            print(f"Adding column: {col}")
            cursor.execute(f"ALTER TABLE books ADD COLUMN {col} REAL")
    
    # 処理済フラグ的なカラムがあれば便利だが、今回は全件一括を想定
    conn.commit()
    conn.close()

def vectorize():
    add_columns()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Fetching records for vectorization...")
    cursor.execute("SELECT rowid, isbn, title, author, publisher, description FROM books")
    records = cursor.fetchall()
    total = len(records)
    print(f"Found {total} records.")

    batch_size = 1000
    updates = []
    
    for i, (rowid, isbn, title, author, publisher, description) in enumerate(records):
        # 1. ERA (1800-2030)
        # Search for year in title or description as fallback
        year = None
        text_for_year = (title or "") + (description or "")
        year_match = re.search(r'(18|19|20)\d{2}', text_for_year)
        if year_match:
            year = int(year_match.group(0))
        
        if year:
            era = (year - 1800) / (2030 - 1800)
        else:
            era = 0.8  # Default (Modern era)
        
        era = clamp(era)
        
        # 2. ORIGIN
        origin = 0.0
        if author:
            if any(char in author for char in ['・', '=', '訳']):
                origin = 1.0
        
        # 3. STYLE
        style = 0.5
        text_for_style = (title or "") + (description or "")
        for k in HARD_KEYWORDS:
            if k in text_for_style:
                style += 0.2
        for k in SOFT_KEYWORDS:
            if k in text_for_style:
                style -= 0.2
        style = clamp(style)
        
        # 4. RENOWN
        renown = 0.3
        if publisher and any(p in publisher for p in MAJOR_PUBLISHERS):
            renown += 0.3
        if description and len(description) > 300:
            renown += 0.3
        renown = clamp(renown)
        
        # Adding Micro-noise
        era = clamp(era + random.uniform(-0.02, 0.02))
        origin = clamp(origin + random.uniform(-0.02, 0.02))
        style = clamp(style + random.uniform(-0.02, 0.02))
        renown = clamp(renown + random.uniform(-0.02, 0.02))
        
        updates.append((era, origin, style, renown, rowid))
        
        if len(updates) >= batch_size:
            cursor.executemany("UPDATE books SET era=?, origin=?, style=?, renown=? WHERE rowid=?", updates)
            conn.commit()
            print(f"Processed: {i+1} / {total}")
            updates = []
            
    if updates:
        cursor.executemany("UPDATE books SET era=?, origin=?, style=?, renown=? WHERE rowid=?", updates)
        conn.commit()
        print(f"Final Batch Processed: {total} / {total}")

    conn.close()
    print("Heuristic vectorization complete.")

if __name__ == "__main__":
    vectorize()
