import sqlite3
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_CONFIGS = {
    "Rakuten": os.path.join(BASE_DIR, "rakuten_raw.db"),
    "openBD": os.path.join(BASE_DIR, "openbd_raw.db"),
    "Google": os.path.join(BASE_DIR, "google_raw.db")
}

def monitor():
    last_counts = {name: 0 for name in DB_CONFIGS}
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"=== lemma Data Acquisition Monitor [{time.strftime('%H:%M:%S')}] ===")
        print("=" * 55)
        
        for name, db_path in DB_CONFIGS.items():
            try:
                if not os.path.exists(db_path):
                    print(f"[{name:8}] Waiting for {db_path}...")
                    continue

                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 総件数の取得
                cursor.execute("SELECT COUNT(*) FROM books")
                count = cursor.fetchone()[0]
                
                # 最新3件の取得
                cursor.execute("SELECT title, author FROM books ORDER BY rowid DESC LIMIT 3")
                recent = cursor.fetchall()
                conn.close()
                
                diff = count - last_counts[name] if last_counts[name] > 0 else 0
                
                print(f"[{name:8}] Total: {count:6} (+{diff:2})")
                for title, author in recent:
                    disp_title = (title[:40] + '..') if len(title) > 40 else title
                    print(f"  > {disp_title}")
                print("-" * 55)
                
                last_counts[name] = count
                
            except Exception as e:
                print(f"[{name:8}] Error: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    monitor()
