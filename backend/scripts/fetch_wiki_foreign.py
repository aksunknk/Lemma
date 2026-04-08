import requests
import re
import time
import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# アプリケーションルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import Book
from database import SessionLocal

# Wikipedia API Endpoint
WIKI_API_URL = "https://ja.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "SingleBookEngineBot/1.0 (contact: your-email@example.com)"}

# 作家リスト（著名な作家50名）
AUTHORS = [
    "フョードル・ドストエフスキー", "レフ・トルストイ", "アントン・チェーホフ", "ヴィクトル・ユーゴー", "アルベール_カミュ",
    "チャールズ・ディケンズ", "ウィリアム・シェイクスピア", "ジョージ・オーウェル", "フランツ・カフカ", "ヘルマン・ヘッセ",
    "ヨハン・ヴォルフガング・フォン・ゲーテ", "ダンテ・アリギエーリ", "ミゲル・デ・セルバンテス", "エドガー・アラン・ポー", "マーク・トウェイン",
    "アーネスト・ヘミングウェイ", "ハーマン・メルヴィル", "ガブリエル・ガルシア＝マルケス", "ホルヘ・ルイス_ボルヘス", "フリオ・コルタサル",
    "マシャード・デ・アシス", "マリオ・バルガス・リョサ", "魯迅", "曹雪芹", "呉承恩", 
    "羅貫中", "ラビンドラナート・タゴール", "プレームチャンド", "オマル・ハイヤーム", "フェルドウスィー",
    "ナギーブ・マフフーズ", "チヌア・アチェベ", "ウォーレ・ショインカ", "オルハン・パムク", "ルミ",
    "アントワーヌ・ド_サン＝テグジュペリ", "ジュール・ヴェルヌ", "アーサー・コナン・ドイル", "アガサ・クリスティ", "ジェーン・オースティン",
    "エミリー・ブロンテ", "F・スコット・フィッツジェラルド", "ジョン・スタインベック", "サマセット・モーム", "オスカー・ワイルド",
    "スタニスワフ・レム", "カレル・チャペック", "ミハイル・ブルガーコフ", "ウンベルト・エーコ", "イタロ・カルヴィーノ"
]

def get_wikipedia_content(title):
    """Wikipediaのページ内容を取得する"""
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "titles": title
    }
    time.sleep(1)
    try:
        response = requests.get(WIKI_API_URL, params=params, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id != "-1":
                    return page_data
        return None
    except Exception:
        return None

def search_works_by_author(author):
    """作家に関連する記事を検索する（より柔軟に）"""
    author_clean = author.replace("_", " ")
    all_titles = set()
    
    # カテゴリ検索 (日本語Wikipediaの一般的なカテゴリ形式)
    cat_queries = [f"{author_clean}の作品", f"{author_clean}の小説", f"{author_clean}", f"Category:{author_clean}"]
    for cat_name in cat_queries:
        title = cat_name if "Category:" in cat_name else f"Category:{cat_name}"
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": title,
            "cmlimit": 50
        }
        time.sleep(1)
        try:
            r = requests.get(WIKI_API_URL, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                members = r.json().get("query", {}).get("categorymembers", [])
                for m in members:
                    if m["ns"] == 0: all_titles.add(m["title"])
        except: continue

    # キーワード検索
    search_queries = [f"{author_clean} 小説", f"{author_clean} 作品"]
    for q in search_queries:
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": q,
            "srlimit": 50
        }
        time.sleep(1)
        try:
            r = requests.get(WIKI_API_URL, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                results = r.json().get("query", {}).get("search", [])
                for res in results: all_titles.add(res["title"])
        except: continue
            
    return list(all_titles)

def extract_year(text):
    """4桁の西暦を抽出する"""
    if not text: return 1900
    # 「18xx年」「19xx年」「20xx年」または「(18xx)」などの形式を広く探す
    match = re.search(r'(\d{4})年', text)
    if match: return int(match.group(1))
    match = re.search(r'\((\d{4})\)', text)
    if match: return int(match.group(1))
    return 1900

def main():
    works_data = []
    titles_seen = set()
    
    print(f"Starting FINAL Wikipedia collection: {len(AUTHORS)} authors...")
    
    for author in AUTHORS:
        author_clean = author.replace("_", " ")
        print(f"-> Processing author: {author_clean} (Current Total: {len(works_data)})")
        work_titles = search_works_by_author(author)
        
        count_for_this_author = 0
        for title in work_titles:
            # 除外条件：既に取得済み、著者自身のページ、一覧ページなど
            if title in titles_seen or title == author_clean: continue
            if any(x in title for x in ["一覧", "リスト", "年表", "カテゴリ"]): continue
            
            content = get_wikipedia_content(title)
            if content and "extract" in content:
                extract = content["extract"]
                if len(extract) < 150: continue # 最低限の長さを担保
                
                works_data.append({
                    "id": f"WIKI_{content['pageid']}",
                    "title": content["title"],
                    "author": author_clean,
                    "description": extract,
                    "era": extract_year(extract),
                    "text_length": len(extract)
                })
                titles_seen.add(title)
                count_for_this_author += 1
                
                if len(works_data) % 50 == 0:
                    print(f"*** STATUS: {len(works_data)} works collected ***")
                
                if count_for_this_author >= 30: break # 分散
        
        if len(works_data) >= 700: break
    
    if len(works_data) < 10:
        print("FATAL: Insufficient data collected.")
        return

    # スケーリングと統合
    lengths = [w["text_length"] for w in works_data]
    max_len, min_len = max(lengths), min(lengths)
    
    db = SessionLocal()
    try:
        print(f"Integrating {len(works_data)} works into database...")
        integrated_count = 0
        for w in works_data:
            pop = (max_len - w["text_length"]) / (max_len - min_len) if max_len != min_len else 0.5
            
            book = db.query(Book).filter(Book.id == w["id"]).first()
            if not book:
                book = Book(id=w["id"])
                db.add(book)
            
            book.title = w["title"]
            book.author = w["author"]
            book.description = w["description"]
            book.era = w["era"]
            book.origin_domestic = False
            book.popularity = pop
            book.style_score = 0.5
            book.category = "WIKI_FOREIGN"
            
            integrated_count += 1
            if integrated_count >= 500: break

        db.commit()
        print(f"DATABASE UPDATE SUCCESSFUL: {integrated_count} records inserted/updated.")
    except Exception as e:
        db.rollback()
        print(f"DB Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
