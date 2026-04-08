import sqlite3
import pandas as pd
import re
import os
from tqdm import tqdm
import requests
import io

DB_PATH = "lemma_manga.db"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

# アワードごとのベクトル設定定数 (style(硬〜平), renown(知名度))
AWARD_CONFIG = {
    "マンガ大賞": (0.5, 0.9),
    "このマンガがすごい！_オトコ編": (0.4, 0.8),
    "このマンガがすごい！_オンナ編": (0.3, 0.8),
    "次にくるマンガ大賞_コミックス部門": (0.3, 0.7),
    "次にくるマンガ大賞_Webマンガ部門": (0.2, 0.7),
    "文化庁メディア芸術祭": (0.9, 0.6),
}

def normalize_era(year_str):
    """年を0.0-1.0に正規化 (1950年〜2025年基準)"""
    try:
        match = re.search(r'(\d{4})', str(year_str))
        if not match: return 0.9
        year_int = int(match.group(1))
        start, end = 1950, 2025
        score = (year_int - start) / (end - start)
        return round(max(0.0, min(1.0, score)), 3)
    except:
        return 0.9

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS manga (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            source TEXT,
            era REAL,
            origin REAL,
            style REAL,
            renown REAL,
            UNIQUE(title, author, source)
        )
    """)
    conn.commit()
    return conn

def fetch_wikipedia_tables(url, source_name):
    """Wikipediaのテーブルを汎用的に取得（User-Agent対応 & MultiIndex対応）"""
    print(f"Fetching: {source_name}...")
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        tables = pd.read_html(io.StringIO(response.text))
        results = []
        
        for df in tables:
            # MultiIndexの平坦化
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [
                    ' '.join([str(level) for level in col if "Unnamed" not in str(level)]).strip() 
                    for col in df.columns.values
                ]
            
            # カラム名リストの取得
            cols = [str(c) for c in df.columns]
            
            # 作品名と作者が含まれているかチェック
            target_title_col = None
            target_author_col = None
            
            for c in df.columns:
                c_str = str(c)
                if any(x in c_str for x in ["作品名", "作品", "タイトル", "書名"]): target_title_col = c
                if any(x in c_str for x in ["作者", "漫画", "著者", "作画"]): target_author_col = c
            
            if target_title_col and target_author_col:
                # 年度/回数カラムを探す
                year_col = None
                for c in df.columns:
                    c_str = str(c)
                    if any(x in c_str for x in ["年", "回"]): year_col = c
                
                for _, row in df.iterrows():
                    try:
                        title_raw = str(row[target_title_col])
                        author_raw = str(row[target_author_col])
                        
                        if title_raw == "nan" or author_raw == "nan": continue
                        
                        # クレンジング (Wikipedia固有の注釈や括弧を削除)
                        title = re.sub(r'\[.*?\]|（.*?）|\(.*?\)', '', title_raw).strip()
                        author = re.sub(r'\[.*?\]|（.*?）|\(.*?\)', '', author_raw).strip()
                        
                        if not title or not author: continue
                        
                        year = 2020 # デフォルト
                        if year_col:
                            year_val = str(row[year_col])
                            year_match = re.search(r'(\d{4})', year_val)
                            if year_match:
                                year = year_match.group(1)
                            elif "回" in year_val:
                                try:
                                    num_match = re.search(r'\d+', year_val)
                                    if num_match:
                                        num = int(num_match.group())
                                        if "マンガ大賞" in source_name: year = 2008 + num - 1
                                        elif "このマンガがすごい" in source_name: year = 2006 + num - 1
                                except: pass

                        results.append({
                            "title": title, "author": author, "source": source_name,
                            "era": normalize_era(year), "origin": 0.0,
                            "style": AWARD_CONFIG.get(source_name, (0.5, 0.5))[0],
                            "renown": AWARD_CONFIG.get(source_name, (0.5, 0.5))[1]
                        })
                    except: continue
        return results
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
        return []

def main():
    db_conn = init_db()
    
    # ターゲットURLリスト
    targets = [
        {"name": "マンガ大賞", "url": "https://ja.wikipedia.org/wiki/%E3%83%9E%E3%83%B3%E3%82%AC%E5%A4%A7%E8%B3%9E"},
        {"name": "このマンガがすごい！_オトコ編", "url": "https://ja.wikipedia.org/wiki/%E3%81%93%E3%81%AE%E3%83%9E%E3%83%B3%E3%82%AC%E3%81%8C%E3%81%99%E3%81%94%E3%81%84!"},
        {"name": "次にくるマンガ大賞_コミックス部門", "url": "https://ja.wikipedia.org/wiki/%E6%AC%A1%E3%81%AB%E3%81%8F%E3%82%8B%E3%83%9E%E3%83%B3%E3%82%AC%E5%A4%A7%E8%B3%9E"},
        {"name": "文化庁メディア芸術祭", "url": "https://ja.wikipedia.org/wiki/%E6%96%87%E5%8C%96%E5%BA%81%E3%83%A1%E3%83%87%E3%82%A3%E3%82%A2%E8%8A%B8%E8%A1%93%E7%A5%AD"},
    ]
    
    total_new_records = 0
    
    for target in targets:
        items = fetch_wikipedia_tables(target["url"], target["name"])
        if not items: continue
        
        print(f"Storing {len(items)} items for {target['name']}...")
        cursor = db_conn.cursor()
        for item in tqdm(items, desc=target["name"]):
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO manga (title, author, source, era, origin, style, renown)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (item['title'], item['author'], item['source'], item['era'], 
                      item['origin'], item['style'], item['renown']))
                if cursor.rowcount > 0:
                    total_new_records += 1
            except: pass
        db_conn.commit()
    
    print(f"\nIntegration Complete. Total new records added: {total_new_records}")
    db_conn.close()

if __name__ == "__main__":
    main()
