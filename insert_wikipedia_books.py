import urllib.request
import urllib.parse
import json
import sqlite3
import sys
import os
import time
import re
import random

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API_URL = "https://ja.wikipedia.org/w/api.php"
DB_PATH = "books.db"

CATEGORIES = [
    "Category:西洋古典文学", "Category:イギリスの小説", "Category:フランスの小説",
    "Category:ロシアの小説", "Category:アメリカ合衆国の小説", "Category:中国の古典小説",
    "Category:インドの文学", "Category:ラテンアメリカの小説", "Category:アフリカの文学",
    "Category:哲学書", "Category:政治思想書", "Category:ドイツの小説", "Category:ラテン文学"
]

EXCLUDE_WORDS = ["年鑑", "白書", "一覧", "の歴史", "の作家"]

def clean_title(title):
    # (小説) などの後ろの括弧を削除
    title = re.sub(r'\s*\(.*?\)$', '', title)
    title = re.sub(r'\s*（.*?）$', '', title)
    return title

def fetch_category_members(category):
    all_pages = []
    cmcontinue = None
    
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "500",
            "cmnamespace": "0", # 標準名前空間（記事）のみ
            "format": "json"
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
            
        query_string = urllib.parse.urlencode(params)
        url = f"{API_URL}?{query_string}"
        
        req = urllib.request.Request(url, headers={"User-Agent": "LemmaProjectEngine/1.0"})
        
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                data = json.loads(res.read().decode("utf-8"))
                
            if "query" in data and "categorymembers" in data["query"]:
                all_pages.extend(data["query"]["categorymembers"])
                
            if "continue" in data and "cmcontinue" in data["continue"]:
                cmcontinue = data["continue"]["cmcontinue"]
                time.sleep(1)
            else:
                break
        except Exception as e:
            time.sleep(1)
            break
            
    return all_pages

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_count = 0
    inserted_titles = []
    inserted_ids = set()
    
    for category in CATEGORIES:
        pages = fetch_category_members(category)
        time.sleep(1)
        
        for page in pages:
            raw_title = page["title"]
            page_id = page["pageid"]
            
            # ノイズフィルター
            if any(ew in raw_title for ew in EXCLUDE_WORDS):
                continue
                    
            c_title = clean_title(raw_title)
            b_id = f"wiki-{page_id}"
            
            if b_id in inserted_ids:
                continue
                
            # 重複チェック(DB)
            cursor.execute("SELECT id FROM books WHERE id=?", (b_id,))
            if cursor.fetchone():
                inserted_ids.add(b_id)
                continue
                
            try:
                # foreign_score = 1.0 (origin_domestic = 1.0 in schema as float/bool 1 for foreign)
                # plain_score = 0.1
                # category = "wikipedia"
                cursor.execute("""
                    INSERT INTO books (id, title, author, description, era, origin_domestic, popularity, style_score, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (b_id, c_title, "Unknown", "", 1900, 1.0, 0.5, 0.1, "wikipedia"))
                new_count += 1
                inserted_titles.append(c_title)
                inserted_ids.add(b_id)
            except sqlite3.IntegrityError:
                pass
                
    conn.commit()
    conn.close()
    
    print(f"NEW_COUNT:{new_count}")
    
    sample_size = min(10, len(inserted_titles))
    if sample_size > 0:
        samples = random.sample(inserted_titles, sample_size)
    else:
        samples = []
    
    for s in samples:
        print(f"SAMPLE:{s}")

if __name__ == "__main__":
    main()
