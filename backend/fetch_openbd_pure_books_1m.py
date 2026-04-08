import requests
import sqlite3
import time
import random
import os
import re

# 定数
DB_PATH = "openbd_supplement.db"
TARGET_COUNT = 1000000
COVERAGE_URL = "https://api.openbd.jp/v1/coverage"
GET_URL = "https://api.openbd.jp/v1/get"
CHUNK_SIZE = 1000

# ノイズキーワード
NOISE_KEYWORDS = ['カレンダー', '手帳', 'ダイアリー', '過去問', 'ドリル', 'パズル', 'コミック', '画集', '写真集', '完全版', '特装版', 'カセット', 'CD']

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

def calculate_heuristics(title, author, publisher, description, pubdate, c_code):
    # 1. ERA
    year = 2020
    if pubdate:
        match = re.search(r'\d{4}', pubdate)
        if match: year = int(match.group(0))
    era = (year - 1800) / (2030 - 1800)
    
    # 2. ORIGIN
    origin = 0.0
    if author and any(char in author for char in ['・', '=', '訳']):
        origin = 1.0
        
    # 3. STYLE
    style = 0.5
    # あらすじが無い場合はタイトルと出版社、Cコードから推測
    text_for_style = (title or "") + (description or "") + (publisher or "")
    for k in HARD_KEYWORDS:
        if k in text_for_style: style += 0.2
    for k in SOFT_KEYWORDS:
        if k in text_for_style: style -= 0.2
        
    # Cコードによる文体補正 (専門書系)
    if c_code and len(c_code) >= 2:
        if c_code.startswith('3'): style += 0.2 # 社会科学
        if c_code.startswith('4'): style += 0.2 # 自然科学
    
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

def fetch_pure_books():
    conn = init_db()
    cursor = conn.cursor()
    
    print("Fetching all ISBNs from openBD coverage...")
    try:
        res = requests.get(COVERAGE_URL, timeout=30)
        all_isbns = res.json()
        random.shuffle(all_isbns)
        print(f"Total ISBNs found: {len(all_isbns)}. Target: {TARGET_COUNT}")
    except Exception as e:
        print(f"Failed to fetch coverage: {e}")
        return

    total_added = 0
    
    for i in range(0, len(all_isbns), CHUNK_SIZE):
        if total_added >= TARGET_COUNT: break
        
        chunk = all_isbns[i:i+CHUNK_SIZE]
        isbn_str = ",".join(chunk)
        
        try:
            # POST request for bulk data
            response = requests.post(GET_URL, data={'isbn': isbn_str}, timeout=30)
            if response.status_code != 200:
                print(f"Error {response.status_code}. Skipping chunk.")
                continue
                
            data = response.json()
            if not data: continue
            
            for book_data in data:
                if total_added >= TARGET_COUNT: break
                if not book_data: continue
                
                summary = book_data.get('summary', {})
                onix = book_data.get('onix', {})
                
                title = summary.get('title', '')
                if not title: continue
                
                # 1. ノイズキーワード除外（タイトル）
                if any(k in title for k in NOISE_KEYWORDS):
                    continue
                
                # 3. Cコードフィルター
                c_code = ""
                try:
                    # ONIX 3.0 or 2.1 structure varies
                    subj = onix.get('DescriptiveDetail', {}).get('Subject', [])
                    for s in subj:
                        if s.get('SubjectSchemeIdentifier') == '78': # C-Code
                            c_code = s.get('SubjectCode', '')
                            break
                    if not c_code:
                        # Alternative path for ONIX 2.1
                        subj = onix.get('Subject', [])
                        for s in subj:
                            if s.get('SubjectSchemeIdentifier') == '78':
                                c_code = s.get('SubjectCode', '')
                                break
                except: pass
                
                if c_code:
                    if c_code.startswith('7') or c_code.startswith('8'):
                        continue # Comic or Children's book
                
                isbn = summary.get('isbn', '')
                author = summary.get('author', '')
                publisher = summary.get('publisher', '')
                pubdate = summary.get('pubdate', '')
                description = summary.get('description', '')
                
                if isbn:
                    era, origin, style, renown = calculate_heuristics(title, author, publisher, description, pubdate, c_code)
                    
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO books (isbn, title, author, publisher, pubdate, description, era, origin, style, renown)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (isbn, title, author, publisher, pubdate, description, era, origin, style, renown))
                        if cursor.rowcount > 0:
                            total_added += 1
                    except: pass
            
            conn.commit()
            print(f"[{time.strftime('%H:%M:%S')}] Progress: {total_added} / {TARGET_COUNT} (Processed {i + len(chunk)} ISBNs)")
            time.sleep(1.0)
            
        except Exception as e:
            print(f"Error processing chunk: {e}")
            time.sleep(5)
            
    conn.close()
    print(f"Finished. Total pure books captured: {total_added}")

if __name__ == "__main__":
    fetch_pure_books()
