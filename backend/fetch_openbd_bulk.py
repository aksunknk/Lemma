import requests
import sqlite3
import time
import os

# フィルトリング定数
MIN_DESC_LEN = 50
EXCLUDE_KEYWORDS = [
    'カレンダー', '手帳', 'ダイアリー', '過去問', 'ドリル', 
    'パズル', 'コミック', '画集', '写真集', '完全版',
    '攻略本', 'ファンブック', '図鑑', 'ムック'
]

DB_PATH = "openbd_raw.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            isbn TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            publisher TEXT,
            description TEXT,
            c_code TEXT
        )
    """)
    conn.commit()
    return conn

def fetch_openbd_bulk():
    conn = init_db()
    cursor = conn.cursor()
    
    # 既存のISBNを取得して重複を避ける
    cursor.execute("SELECT isbn FROM books")
    existing_isbns = set(row[0] for row in cursor.fetchall())
    
    print("Fetching ISBN coverage from openBD...")
    coverage_url = "https://api.openbd.jp/v1/coverage"
    try:
        all_isbns = requests.get(coverage_url, timeout=30).json()
    except Exception as e:
        print(f"Failed to fetch coverage: {e}")
        return

    # 未取得のISBNのみをフィルタリング
    isbns_to_fetch = [isbn for isbn in all_isbns if isbn not in existing_isbns]
    print(f"Total ISBNs: {len(all_isbns)}, To Fetch: {len(isbns_to_fetch)}")

    chunk_size = 1000
    for i in range(0, len(isbns_to_fetch), chunk_size):
        chunk = isbns_to_fetch[i : i + chunk_size]
        url = "https://api.openbd.jp/v1/get"
        
        try:
            # POSTリクエストで一括取得
            response = requests.post(url, data={'isbn': ','.join(chunk)}, timeout=60)
            if response.status_code != 200:
                print(f"Error {response.status_code} at chunk {i}")
                time.sleep(10)
                continue
                
            data = response.json()
            if not data:
                continue

            valid_count = 0
            for entry in data:
                if not entry: continue
                
                summary = entry.get('summary', {})
                onix = entry.get('onix', {})
                
                isbn = summary.get('isbn')
                title = summary.get('title', '')
                author = summary.get('author', '')
                publisher = summary.get('publisher', '')
                
                # Cコードの取得
                c_code = ""
                classifications = onix.get('DescriptiveDetail', {}).get('Subject', [])
                for sub in classifications:
                    if sub.get('SubjectSchemeIdentifier') == '78': # C-Code
                        c_code = sub.get('SubjectCode', '')
                        break
                
                # 品質ゲート1: Cコードによる除外
                if c_code:
                    # 71 (コミック), 72 (学参), 73 (児童書), 74 (社会), 75 (実用), 76 (サイエンス)
                    # 文芸・一般書を優先するため、コミック(71)や学習参考書(72)を厳格に排除
                    if c_code.startswith('71') or c_code.startswith('72'):
                        continue

                # 品質ゲート2: タイトルキーワードによる除外
                if any(k in title for k in EXCLUDE_KEYWORDS):
                    continue
                
                # 品質ゲート3: あらすじ（TextContent）の取得と長さ判定
                description = ""
                text_contents = onix.get('CollateralDetail', {}).get('TextContent', [])
                for tc in text_contents:
                    if tc.get('TextType') == '03': # Description
                        description = tc.get('Text', '')
                        break
                
                if not description:
                    # summaryのコンテンツも確認
                    description = entry.get('summary', {}).get('content', '')
                
                # HTMLタグの除去（簡易的）
                import re
                description = re.sub('<[^<]+?>', '', description)
                
                if len(description) < MIN_DESC_LEN:
                    continue
                
                # 保存
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO books (isbn, title, author, publisher, description, c_code)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (isbn, title, author, publisher, description, c_code))
                    if cursor.rowcount > 0:
                        valid_count += 1
                except Exception as e:
                    print(f"DB Insert Error: {e}")
            
            conn.commit()
            print(f"[{time.strftime('%H:%M:%S')}] Processed {i+chunk_size}/{len(isbns_to_fetch)} | Added: {valid_count}")
            
            # サーバー負荷軽減
            time.sleep(2.0)
            
        except Exception as e:
            print(f"Request Error at chunk {i}: {e}")
            time.sleep(10)

    conn.close()
    print("Bulk fetch complete.")

if __name__ == "__main__":
    fetch_openbd_bulk()
