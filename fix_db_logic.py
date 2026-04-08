import sqlite3
import os

def fix_logic():
    db_path = "books.db"
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # origin_domestic カラムの論理を反転（国内 1 -> 0, 海外 0 -> 1）
    cursor.execute("UPDATE books SET origin_domestic = ABS(origin_domestic - 1)")
    conn.commit()
    print(f"既存データのスコア論理反転完了: {cursor.rowcount}件")
    conn.close()

if __name__ == "__main__":
    fix_logic()
