import sqlite3
import time
import os

DB_PATH = "lemma_manga.db"

def monitor():
    while True:
        if not os.path.exists(DB_PATH):
            print("Waiting for database creation...")
            time.sleep(2)
            continue
            
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # ソース別の件数
            cursor.execute("SELECT source, COUNT(*) FROM manga GROUP BY source")
            source_counts = cursor.fetchall()
            
            # 合計件数
            cursor.execute("SELECT COUNT(*) FROM manga")
            total = cursor.fetchone()[0]
            
            # 画面クリア (Windows/Unix)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 50)
            print(" LEMMA MANGA DB MONITORING ")
            print("=" * 50)
            print(f"{'Source':<35} | {'Count':>10}")
            print("-" * 50)
            
            for src, count in source_counts:
                print(f"{src:<35} | {count:>10,}")
                
            print("-" * 50)
            print(f"{'TOTAL':<35} | {total:>10,}")
            print("=" * 50)
            print(f"Last Update: {time.strftime('%H:%M:%S')}")
            print("Press Ctrl+C to stop monitor.")
            
            conn.close()
        except Exception as e:
            print(f"Monitor Error: {e}")
            
        time.sleep(1)

if __name__ == "__main__":
    monitor()
