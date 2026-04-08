import sqlite3
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import time
import random

DB_PATH = "lemma_manga.db"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

def normalize_era(year_str):
    try:
        match = re.search(r"(\d{4})", str(year_str))
        if not match: return 0.5
        year = int(match.group(1))
        era = (year - 2000) / (2024 - 2000)
        return max(0.0, min(1.0, era))
    except:
        return 0.5

def save_manga(conn, title, author, source, era, origin=0.0, style=0.5, renown=0.8):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO manga (title, author, source, era, origin, style, renown)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, author, source, era, origin, style, renown))
        conn.commit()
        return 1 if cursor.rowcount > 0 else 0
    except:
        return 0

def fetch_kono_manga(conn):
    """「このマンガがすごい！」の過去年分を取得 (修正版)"""
    print("Scraping 'Kono Manga ga Sugoi!' (Expansion Fix)...")
    url = "https://ja.wikipedia.org/wiki/%E3%81%93%E3%81%AE%E3%83%9E%E3%83%B3%E3%82%AC%E3%81%8C%E3%81%99%E3%81%94%E3%81%84%EF%BC%81"
    
    response = requests.get(url, headers=HEADERS)
    tables = pd.read_html(response.text)
    
    new_count = 0
    for idx, source_name in [(0, "このマンガがすごい！_オトコ編"), (1, "このマンガがすごい！_オンナ編")]:
        df = tables[idx]
        current_year = "2024"
        
        for _, row in df.iterrows():
            # 修正: 最初のセルまたは全セルの値が4桁の数値（年）のみの場合を検知
            first_val = str(row[0]).strip()
            # "2024" や "2024年" に対応
            year_match = re.fullmatch(r"(\d{4})(年)?.*", first_val)
            
            # ヘッダー判定: 4桁の数値で始まり、かつ「位」や「タイトル」を含まない
            if year_match and not any(x in first_val for x in ["位", "タイトル", "順位"]):
                current_year = year_match.group(1)
                continue
            
            try:
                rank_str = str(row[0])
                # 「1位」や「1」から始まる行、かつタイトルが存在する行
                if (any(x in rank_str for x in ["位", "1", "2", "3"]) or rank_str.isdigit()) and len(str(row[1])) > 1:
                    title = str(row[1]).strip()
                    author = str(row[2]).strip()
                    title = re.sub(r"\[\d+\]", "", title)
                    author = re.sub(r"\[\d+\]", "", author)
                    
                    if 2010 <= int(current_year) <= 2025:
                        era = normalize_era(current_year)
                        new_count += save_manga(conn, title, author, source_name, era, renown=0.9)
            except: continue
    return new_count

def fetch_manga_taisho(conn):
    """「マンガ大賞」の2010-2024を取得 (修正版)"""
    print("Scraping 'Manga Taisho' (Robust Parser)...")
    url = "https://ja.wikipedia.org/wiki/%E3%83%9E%E3%83%B3%E3%82%AC%E5%A4%A7%E8%B3%9賞"
    
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    new_count = 0
    
    for year in range(2010, 2025):
        era = normalize_era(year)
        # 括弧の全角半角に柔軟に対応
        pattern = re.compile(f".*[{re.escape('（(')}]{year}年[{re.escape('）)')}].*")
        heading = soup.find(lambda tag: tag.name in ["h3", "h4"] and pattern.search(tag.text))
        if not heading: continue
        
        # 連続する ul (大賞とノミネート) を取得
        curr = heading.next_sibling
        while curr and curr.name not in ["h3", "h4"]:
            if curr.name == "ul":
                for li in curr.find_all("li"):
                    text = li.text
                    match = re.search(r"「(.+?)」\s*[（(](.+?)[）)]", text)
                    if match:
                        title, author = match.groups()
                        new_count += save_manga(conn, title, author, "マンガ大賞", era)
            curr = curr.next_sibling
    return new_count

def fetch_media_arts(conn):
    """文化庁メディア芸術祭 マンガ部門"""
    print("Scraping 'Media Arts Festival'...")
    url = "https://ja.wikipedia.org/wiki/%E6%96%87%E5%8C%96%E5%BA%81%E3%83%A1%E3%83%87%E3%82%A3%E3%82%A2%E8%8A%B8%E8%A1%93%E7%A5%AD"
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    new_count = 0
    
    # 手動で「マンガ部門」のセクション以降をパース
    section = soup.find(id="マンガ部門")
    if section:
        table = section.find_next("table", {"class": "wikitable"})
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all(["td", "th"])
                if len(cols) >= 3:
                    title = cols[1].get_text(strip=True)
                    author = cols[2].get_text(strip=True)
                    if title and author and "作品" not in title:
                        new_count += save_manga(conn, title, author, "文化庁メディア芸術祭", 0.6, origin=0.4)
    return new_count

def fetch_afternoon(conn):
    """Phase 4: 月刊アフタヌーン連載作品 (Wikipedia)"""
    print("Scraping 'Monthly Afternoon' List...")
    url = "https://ja.wikipedia.org/wiki/%E6%9C%88%E5%88%8A%E3%82%A2%E3%83%95%E3%82%BF%E3%83%8C%E3%83%BC%E3%83%B3%E9%80%A3%E8%BC%89%E4%BD%9C%E5%93%81%E4%B8%80%E8%A6%A7"
    response = requests.get(url, headers=HEADERS)
    tables = pd.read_html(response.text)
    new_count = 0
    for df in tables:
        if "作品名" in df.columns and "作者（作画）" in df.columns:
            for _, row in df.iterrows():
                title = str(row["作品名"]).strip()
                author = str(row["作者（作画）"]).strip()
                if title and author and title != "nan":
                    new_count += save_manga(conn, title, author, "月刊アフタヌーン", 0.8, origin=0.8, renown=0.6)
    return new_count

def main():
    conn = init_db()
    try:
        # Phase 3
        k = fetch_kono_manga(conn); print(f"Kono Manga: +{k}")
        t = fetch_manga_taisho(conn); print(f"Manga Taisho: +{t}")
        ma = fetch_media_arts(conn); print(f"Media Arts: +{ma}")
        
        # Phase 4 (Continuous Execution)
        af = fetch_afternoon(conn); print(f"Afternoon: +{af}")
        
    except Exception as e:
        print(f"Panic: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
