import sqlite3
import os

DB_PATH = "new_books_2024_2026.db"

def check_status():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 2024年以降の全件数
    cursor.execute("SELECT COUNT(*) FROM books WHERE pub_date >= '20240101'")
    total_2024_2026 = cursor.fetchone()[0]
    
    # データの最新と最古（スキャンした範囲）
    cursor.execute("SELECT MIN(pub_date), MAX(pub_date) FROM books")
    min_date, max_date = cursor.fetchone()
    
    # 最近追加された5件
    cursor.execute("SELECT isbn, title, pub_date FROM books ORDER BY isbn DESC LIMIT 5")
    recent = cursor.fetchall()
    
    print(f"REPORT_START")
    print(f"TOTAL_COUNT={total_2024_2026}")
    print(f"DATE_RANGE={min_date} to {max_date}")
    print(f"RECENT_SAMPLES={recent}")
    print(f"REPORT_END")
    
    conn.close()

if __name__ == "__main__":
    check_status()
