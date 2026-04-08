import requests
import sqlite3
import time
import re
import random
import os

# 定数
DB_PATH = "google_raw.db"
TARGET_COUNT = 50000
API_ENDPOINT = "https://www.googleapis.com/books/v1/volumes"
PUBLISHERS = ['講談社', '集英社', 'KADOKAWA', '小学館', '文藝春秋', '新潮社', '岩波書店', '光文社', '中央公論新社', '早川書房', '東京創元社', '幻冬舎', 'ダイヤモンド社', '東洋経済新報社', '筑摩書房', 'みすず書房']
YEARS = range(1990, 2026)

# ベクトル化用キーワード
HARD_KEYWORDS = ['論', '考', '研究', '史', '哲学', '社会', '思想', '構造', '経済', '政治', '理論', '技術', '科学']
SOFT_KEYWORDS = ['異世界', '転生', '魔法', '少女', '恋', 'ちゃん', 'ダンジョン', 'ラブコメ', 'ふあふあ', 'まったり', 'ほのぼの']
MAJOR_PUBLISHERS = ['講談社', '集英社', 'KADOKAWA', '小学館', '文藝春秋', '新潮社', '学研', 'ポプラ社', '岩波書店', '筑摩書房']

def clamp(n, minn=0.0, maxn=1.0):
    return max(min(maxn, n), minn)

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            isbn TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            publisher TEXT,
            pubdate TEXT,
            description TEXT,
            era REAL,
            origin REAL,
            style REAL,
            renown REAL
        )
    """)
    conn.commit()
    return conn

def calculate_heuristics(title, author, publisher, description, pubdate):
    # 1. ERA
    year = 2020
    if pubdate:
        match = re.search(r'\d{4}', pubdate)
        if match:
            year = int(match.group(0))
    era = (year - 1800) / (2030 - 1800)
    
    # 2. ORIGIN
    origin = 0.0
    if author and any(char in author for char in ['・', '=', '訳']):
        origin = 1.0
        
    # 3. STYLE
    style = 0.5
    text_for_style = (title or "") + (description or "")
    for k in HARD_KEYWORDS:
        if k in text_for_style: style += 0.2
    for k in SOFT_KEYWORDS:
        if k in text_for_style: style -= 0.2
    style = clamp(style)
    
    # 4. RENOWN
    renown = 0.3
    if publisher and any(p in publisher for p in MAJOR_PUBLISHERS):
        renown += 0.3
    if description and len(description) > 300:
        renown += 0.3
    renown = clamp(renown)
    
    # Noise
    era = clamp(era + random.uniform(-0.02, 0.02))
    origin = clamp(origin + random.uniform(-0.02, 0.02))
    style = clamp(style + random.uniform(-0.02, 0.02))
    renown = clamp(renown + random.uniform(-0.02, 0.02))
    
    return era, origin, style, renown

def fetch_google_books():
    conn = init_db()
    cursor = conn.cursor()
    
    total_added = 0
    
    for pub in PUBLISHERS:
        if total_added >= TARGET_COUNT: break
            
        print(f"[{time.strftime('%H:%M:%S')}] Sniping: {pub} | Total: {total_added} / {TARGET_COUNT}")
        
        for start_index in range(0, 1000, 40):
            if total_added >= TARGET_COUNT: break
            
            params = {
                'q': f'inpublisher:{pub}',
                'langRestrict': 'ja',
                'startIndex': start_index,
                'maxResults': 40
            }
            
            try:
                res = requests.get(API_ENDPOINT, params=params, timeout=10)
                if res.status_code == 429:
                    print("Rate limit. Sleeping...")
                    time.sleep(30)
                    continue
                if res.status_code != 200: 
                    print(f"API Error: {res.status_code}")
                    break
                    
                data = res.json()
                items = data.get('items', [])
                if not items: 
                    break
                
                for item in items:
                    vol = item.get('volumeInfo', {})
                    title = vol.get('title', '')
                    authors = vol.get('authors', [])
                    author = authors[0] if authors else ""
                    pub_name = vol.get('publisher', '')
                    pubdate = vol.get('publishedDate', '') or ""
                    description = vol.get('description', '')
                    
                    # 品質ゲート: 日本語・ひらがな絶対防壁
                    combined_text = title + (description or "")
                    if not re.search(r'[\u3040-\u309F]', combined_text):
                        continue

                    # 品質ゲート: あらすじ緩和（10文字以上）
                    if not description or len(description) < 10:
                        continue

                    isbns = vol.get('industryIdentifiers', [])
                    isbn = None
                    for id_item in isbns:
                        if id_item.get('type') in ['ISBN_13', 'ISBN_10']:
                            isbn = id_item.get('identifier')
                            break
                    
                    if isbn:
                        era, origin, style, renown = calculate_heuristics(title, author, pub_name, description, pubdate)
                        
                        try:
                            cursor.execute("""
                                INSERT OR IGNORE INTO books (isbn, title, author, publisher, pubdate, description, era, origin, style, renown)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (isbn, title, author, pub_name, pubdate, description, era, origin, style, renown))
                            
                            if cursor.rowcount > 0:
                                total_added += 1
                                if total_added >= TARGET_COUNT:
                                    conn.commit()
                                    print(f"Goal reached: {TARGET_COUNT}")
                                    return
                        except: pass
                            
                conn.commit()
                time.sleep(1.0)
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)
    conn.close()

if __name__ == "__main__":
    fetch_google_books()
