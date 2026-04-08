import requests
import sqlite3
import time
import sys

# Constants
API_ENDPOINT = "https://openapi.rakuten.co.jp/services/api/BooksBook/Search/20170404"
APPLICATION_ID = "1e8295a9-d120-4d69-8858-5a7dd47de0ed"
ACCESS_KEY = "pk_wASmVrd9ypC5uVs3OpAoIVRJpi11ZX0rLiFiJh53ehX"
GENRES = ['001004', '001017', '001006']
HIRAGANA = [
    'あ','い','う','え','お','か','き','く','け','こ',
    'さ','し','す','せ','そ','た','ち','つ','て','と',
    'な','に','ぬ','ね','の','は','ひ','ふ','へ','ほ',
    'ま','み','む','め','も','や','ゆ','よ','ら','り',
    'る','れ','ろ','わ','を','ん'
]

DB_PATH = "rakuten_raw.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            isbn TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            publisher TEXT,
            salesDate TEXT,
            itemCaption TEXT,
            genreId TEXT
        )
    """)
    conn.commit()
    return conn

def fetch_books():
    conn = init_db()
    cursor = conn.cursor()
    
    total_count = 0
    
    # Get current count
    cursor.execute("SELECT COUNT(*) FROM books")
    total_count = cursor.fetchone()[0]
    
    print(f"Starting batch fetch. Current records: {total_count}")
    
    for genre in GENRES:
        for char in HIRAGANA:
            for page in range(1, 31):
                try:
                    params = {
                        "applicationId": APPLICATION_ID,
                        "accessKey": ACCESS_KEY,
                        "format": "json",
                        "booksGenreId": genre,
                        "title": char,
                        "page": page,
                        "hits": 30,
                        "sort": "standard"
                    }
                    
                    headers = {
                        'Referer': 'http://example.com/',
                        'Origin': 'http://example.com',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    response = requests.get(API_ENDPOINT, params=params, headers=headers, timeout=10)
                    
                    if response.status_code == 429:
                        print("Rate limit exceeded (429). Sleeping longer (15s)...")
                        time.sleep(15)
                        continue
                        
                    if response.status_code != 200:
                        print(f"Error {response.status_code} for Genre:{genre}, Char:{char}, Page:{page}")
                        print(f"Response Body: {response.text}")
                        break # Skip to next character if error
                        
                    data = response.json()
                    items = data.get("Items", [])
                    
                    if not items:
                        # No more items for this character/genre
                        break
                        
                    new_items_in_page = 0
                    for item_wrapper in items:
                        item = item_wrapper.get("Item", {})
                        isbn = item.get("isbn")
                        title = item.get("title")
                        author = item.get("author")
                        publisher = item.get("publisherName")
                        sales_date = item.get("salesDate")
                        caption = item.get("itemCaption")
                        genre_id = item.get("booksGenreId")
                        
                        if isbn and caption: # Only save if we have ISBN and synopsis
                            try:
                                cursor.execute("""
                                    INSERT OR IGNORE INTO books (isbn, title, author, publisher, salesDate, itemCaption, genreId)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (isbn, title, author, publisher, sales_date, caption, genre_id))
                                if cursor.rowcount > 0:
                                    new_items_in_page += 1
                                    total_count += 1
                            except Exception as e:
                                print(f"DB Error: {e}")
                    
                    conn.commit()
                    print(f"ジャンル: {genre}, 文字: {char}, ページ: {page}, 新規取得: {new_items_in_page}, 合計: {total_count}件")
                    
                    # Rate limit safety
                    time.sleep(1.5)
                    
                except requests.exceptions.RequestException as e:
                    print(f"Request error: {e}")
                    time.sleep(5)
                    continue
                except Exception as e:
                    print(f"Unexpected error: {e}")
                    time.sleep(5)
                    continue

    conn.close()
    print("Batch processing finished.")

if __name__ == "__main__":
    fetch_books()
