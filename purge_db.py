import sqlite3
import os

def purge():
    db_path = "books.db"
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books")
    conn.commit()
    print(f"汚染データの完全消去完了: {cursor.rowcount}件削除")
    conn.close()

if __name__ == "__main__":
    purge()
