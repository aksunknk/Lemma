import requests
import sqlite3
import time
import os
import json
import re

DB_PATH = "new_books_2024_2026.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # シンプルかつ網羅的なスキーマ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            isbn TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            publisher TEXT,
            pub_date TEXT,
            series TEXT,
            raw_json TEXT
        )
    """)
    conn.commit()
    return conn

def fetch_recent_bulk():
    conn = init_db()
    cursor = conn.cursor()
    
    # 既存のISBNを取得して重複を避ける
    cursor.execute("SELECT isbn FROM books")
    already_done = set(row[0] for row in cursor.fetchall())
    
    print(f"Starting High-Volume New Book Fetch (2024-2026)...")
    
    # OpenBDの全カバレッジを取得
    coverage_url = "https://api.openbd.jp/v1/coverage"
    try:
        all_isbns = requests.get(coverage_url, timeout=30).json()
        # 日本のISBN (9784...) に限定し、最新順にソート
        jp_isbns = [isbn for isbn in all_isbns if isbn.startswith("9784")]
        jp_isbns.sort(reverse=True) 
    except Exception as e:
        print(f"Failed to fetch coverage: {e}")
        return

    # 未取得のものに限定
    to_fetch = [isbn for isbn in jp_isbns if isbn not in already_done]
    print(f"Total JP ISBNs: {len(jp_isbns)}, To Fetch: {len(to_fetch)}")

    chunk_size = 1000
    stop_count = 0
    max_stop = 30 # 3万件連続で2024年以前なら終了

    for i in range(0, len(to_fetch), chunk_size):
        chunk = to_fetch[i : i + chunk_size]
        url = "https://api.openbd.jp/v1/get"
        
        try:
            response = requests.post(url, data={'isbn': ','.join(chunk)}, timeout=60)
            if response.status_code != 200:
                print(f"Error {response.status_code} at chunk {i}. Retrying...")
                time.sleep(10)
                continue
                
            data = response.json()
            if not data or not isinstance(data, list): continue

            valid_count = 0
            has_new_book_in_chunk = False
            
            for entry in data:
                if not entry or not isinstance(entry, dict): continue
                
                summary = entry.get('summary', {})
                onix = entry.get('onix', {})
                if not isinstance(summary, dict): continue
                
                isbn = summary.get('isbn')
                title = summary.get('title', '')
                author = summary.get('author', '')
                publisher = summary.get('publisher', '')
                pub_date = summary.get('pubdate', '') 
                
                # pub_date の正規化（比較用）
                clean_date = re.sub(r'[^0-9]', '', pub_date)
                
                # 2024年以降かどうか判定
                is_recent = False
                if len(clean_date) >= 4:
                    try:
                        year = int(clean_date[:4])
                        if year >= 2024:
                            is_recent = True
                    except:
                        pass
                
                if is_recent:
                    has_new_book_in_chunk = True
                    
                    # 追加情報の取得
                    series = ""
                    titles = onix.get('DescriptiveDetail', {}).get('TitleDetail', [])
                    if isinstance(titles, list):
                        for td in titles:
                            if td.get('TitleType') == '01':
                                elements = td.get('TitleElement', [])
                                if isinstance(elements, list):
                                    for te in elements:
                                        if te.get('TitleElementLevel') == '02':
                                            series = te.get('TitleText', {}).get('content', '')
                    
                    # 保存
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO books (isbn, title, author, publisher, pub_date, series, raw_json)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (isbn, title, author, publisher, clean_date, series, json.dumps(entry, ensure_ascii=False)))
                        if cursor.rowcount > 0:
                            valid_count += 1
                    except:
                        pass
            
            conn.commit()
            if valid_count > 0:
                stop_count = 0 
                print(f"[{time.strftime('%H:%M:%S')}] Chunk {i//chunk_size} | Added: {valid_count}")
            
            if not has_new_book_in_chunk and i > 5000: # 最初の数チャンクは飛ばしがある可能性があるので5000件以降で判定
                stop_count += 1
                if stop_count >= max_stop:
                    print(f"Coverage complete for 2024-2026.")
                    break
            
            time.sleep(1.2)
            
        except Exception as e:
            print(f"Request Error at chunk {i}: {e}")
            time.sleep(5)

    conn.close()
    print("New book collection (2024-2026) complete.")

if __name__ == "__main__":
    fetch_recent_bulk()
