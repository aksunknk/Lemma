import sqlite3
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "google_raw.db")

def monitor_google():
    last_count = 0
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"=== lemma Google Books - Japanese Quality Monitor [{time.strftime('%H:%M:%S')}] ===")
        print("=" * 65)
        
        try:
            if not os.path.exists(DB_PATH):
                print(f"Waiting for {DB_PATH} to be created...")
                time.sleep(5)
                continue

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # 総件数の取得
            cursor.execute("SELECT COUNT(*) FROM books")
            count = cursor.fetchone()[0]
            
            # 最新5件の取得（日本語性の視認用）
            cursor.execute("SELECT title, author FROM books ORDER BY rowid DESC LIMIT 5")
            recent = cursor.fetchall()
            conn.close()
            
            diff = count - last_count if last_count > 0 else 0
            
            print(f"Total Quality Records: {count:6} ({'+' if diff >= 0 else ''}{diff} since last check)")
            print("-" * 65)
            print("Recently Added (Verify Hiragana):")
            for title, author in recent:
                disp_title = (title[:50] + '..') if len(title) > 50 else title
                print(f"  > {disp_title}")
            
            last_count = count
            
        except Exception as e:
            print(f"Monitor error: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    monitor_google()
