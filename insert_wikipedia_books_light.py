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

BASE_CATEGORIES = [
    "Category:各国の推理小説", "Category:サスペンス小説", "Category:スリラー小説", "Category:スパイ小説", "Category:ハードボイルド小説",
    "Category:各国のSF小説", "Category:各国のファンタジー小説", "Category:ダーク・ファンタジー",
    "Category:ホラー小説", "Category:冒険小説", "Category:アクション小説",
    "Category:恋愛小説", "Category:ロマンス小説", "Category:ユーモア小説", "Category:青春小説",
    "Category:ヤングアダルト小説", "Category:児童文学", "Category:中国のネット小説", "Category:韓国の小説", "Category:台湾の小説"
]

EXCLUDE_WORDS = ["一覧", "の作家", "の歴史", "の登場人物", "のキャラクター"]

def clean_title(title):
    title = re.sub(r'\s*[\(（].*?[\)）]$', '', title)
    return title.strip()

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT title FROM books")
    existing_titles = {row[0] for row in cursor.fetchall() if row[0]}
    
    visited_cats = set()
    queue = [(c, 0) for c in BASE_CATEGORIES]
    
    pages_dict = {}
    
    print("Gathering pages from categories...")
    while queue:
        cat, depth = queue.pop(0)
        if cat in visited_cats:
            continue
        visited_cats.add(cat)
        
        if depth > 2:
            continue
            
        if "日本" in cat:
            continue
            
        cmcontinue = None
        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": cat,
                "cmlimit": "max",
                "format": "json"
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue
            try:
                url = f"{API_URL}?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers={"User-Agent": "LemmaProjectEngine/3.0"})
                with urllib.request.urlopen(req, timeout=10) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    
                for cm in data.get("query", {}).get("categorymembers", []):
                    if cm["ns"] == 0:
                        pages_dict[cm["pageid"]] = cm["title"]
                    elif cm["ns"] == 14:
                        if "日本" not in cm["title"]:
                            queue.append((cm["title"], depth + 1))
                            
                if "continue" in data and "cmcontinue" in data["continue"]:
                    cmcontinue = data["continue"]["cmcontinue"]
                else:
                    break
            except Exception as e:
                break
            time.sleep(0.5)

    print(f"Total pure pages collected: {len(pages_dict)}")
    
    page_ids = list(pages_dict.keys())
    valid_pages = []
    
    print("Checking categories for each page to exclude domestic (日本)...")
    for chunk in chunker(page_ids, 50):
        params = {
            "action": "query",
            "prop": "categories",
            "pageids": "|".join(map(str, chunk)),
            "cllimit": "max",
            "format": "json"
        }
        try:
            url = f"{API_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "LemmaProjectEngine/3.0"})
            with urllib.request.urlopen(req, timeout=10) as res:
                data = json.loads(res.read().decode("utf-8"))
                
            pages_data = data.get("query", {}).get("pages", {})
            for pid_str, pinfo in pages_data.items():
                is_japanese = False
                cats = pinfo.get("categories", [])
                for c in cats:
                    if "日本" in c.get("title", ""):
                        is_japanese = True
                        break
                if not is_japanese:
                    valid_pages.append((pid_str, pinfo.get("title", "")))
        except Exception as e:
            pass
        time.sleep(0.5)

    print(f"Valid overseas pages: {len(valid_pages)}")
    
    new_count = 0
    inserted_titles = []
    
    for pid_str, raw_title in valid_pages:
        if any(ew in raw_title for ew in EXCLUDE_WORDS):
            continue
            
        title = clean_title(raw_title)
        if title in existing_titles:
            continue
            
        book_id = f"wiki_light-{pid_str}"
        
        try:
            cursor.execute("""
                INSERT INTO books (id, title, author, description, era, origin_domestic, popularity, style_score, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (book_id, title, "Unknown", "", 1900, 1.0, 0.5, 0.8, "wikipedia_light"))
            
            existing_titles.add(title)
            new_count += 1
            inserted_titles.append(title)
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    
    sample_size = min(10, len(inserted_titles))
    samples = random.sample(inserted_titles, sample_size) if sample_size > 0 else []
    
    out_text = f"Wikipediaから第一象限用として books.db に「新規追加（差分登録）」された総件数: {new_count}件\n"
    if samples:
        out_text += "登録されたタイトルのサンプル:\n"
        for s in samples:
            out_text += f"  - {s}\n"
            
    with open('stats_light_out.txt', 'w', encoding='utf-8') as f:
        f.write(out_text)

if __name__ == "__main__":
    main()
