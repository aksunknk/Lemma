import sqlite3
import random

def fix_era_data():
    db_path = 'books.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- Era Data Repair Patch ---")

    # 全レコードを取得
    cursor.execute("SELECT id, title, plain_score FROM books")
    rows = cursor.fetchall()
    
    total_count = len(rows)
    classic_count = 0
    modern_count = 0
    
    updates = []
    
    for row in rows:
        book_id, title, plain_score = row
        
        # ヒューリスティック・ルール
        # 1. ID が 'aozora-' で始まる場合は古典
        # 2. plain_score が 0.3 未満 (硬質な文体) の場合は古典
        if (book_id and book_id.startswith('aozora-')) or (plain_score is not None and plain_score < 0.3):
            # 古典判定 (0.1 〜 0.3 のランダム)
            era_val = round(random.uniform(0.1, 0.3), 4)
            classic_count += 1
        else:
            # 現代判定 (0.8 〜 1.0 のランダム)
            era_val = round(random.uniform(0.8, 1.0), 4)
            modern_count += 1
            
        updates.append((era_val, book_id))

    # 一括更新
    cursor.executemany("UPDATE books SET era=? WHERE id=?", updates)
    conn.commit()
    conn.close()

    print(f"Update Complete.")
    print(f"Total processed: {total_count}")
    print(f" - Classic (0.1-0.3): {classic_count}")
    print(f" - Modern (0.8-1.0): {modern_count}")
    
    return total_count

if __name__ == "__main__":
    count = fix_era_data()
    print(f"{count} records updated in database.")
