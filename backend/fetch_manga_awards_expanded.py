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
    """2000-2024年を 0.0-1.0 に正規化"""
    try:
        match = re.search(r"(\d{4})", str(year_str))
        if not match: return 0.5
        year = int(match.group(1))
        era = (year - 2000) / (2024 - 2000)
        return max(0.0, min(1.0, era))
    except:
        return 0.5

def save_manga(conn, title, author, source, era):
    cursor = conn.cursor()
    origin = 0.0 # 国内
    style = 0.5
    renown = 0.9 # アワード受賞作なので知名度は高い
    
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
    """「このマンガがすごい！ (拡張版)」の過去年分を取得"""
    print("Scraping 'Kono Manga ga Sugoi!' (Expansion)...")
    url = "https://ja.wikipedia.org/wiki/%E3%81%93%E3%81%AE%E3%83%9E%E3%83%B3%E3%82%AC%E3%81%8C%E3%81%99%E3%81%94%E3%81%84%EF%BC%81"
    
    response = requests.get(url, headers=HEADERS)
    tables = pd.read_html(response.text)
    
    new_count = 0
    # Table 0: オトコ編, Table 1: オンナ編
    for idx, source_name in [(0, "このマンガがすごい！_オトコ編"), (1, "このマンガがすごい！_オンナ編")]:
        df = tables[idx]
        current_year = "2024"
        
        for _, row in df.iterrows():
            first_val = str(row[0]).strip()
            # ヘッダー行判定 (2024, 2024年, 等)
            year_match = re.fullmatch(r"(\d{4})(年)?.*", first_val)
            
            if year_match and not any(x in first_val for x in ["位", "タイトル"]):
                current_year = year_match.group(1)
                continue
            
            try:
                rank_str = str(row[0])
                if any(x in rank_str for x in ["位", "1", "2", "3"]) and len(str(row[1])) > 1:
                    title = str(row[1]).strip()
                    author = str(row[2]).strip()
                    title = re.sub(r"\[\d+\]", "", title)
                    author = re.sub(r"\[\d+\]", "", author)
                    
                    if 2010 <= int(current_year) <= 2025: # 範囲を広げる
                        era = normalize_era(current_year)
                        new_count += save_manga(conn, title, author, source_name, era)
            except: continue
    return new_count

def fetch_media_arts(conn):
    """文化庁メディア芸術祭 マンガ部門の主要受賞作を取得"""
    print("Scraping 'Media Arts Festival'...")
    url = "https://ja.wikipedia.org/wiki/%E6%96%87%E5%8C%96%E5%BA%81%E3%83%A1%E3%83%87%E3%82%A3%E3%82%A2%E8%8A%B8%E8%A1%93%E7%A5%AD"
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    new_count = 0
    
    # 「マンガ部門」セクション
    section = soup.find(id="マンガ部門")
    if section:
        # 年度ごとの受賞リストが含まれるテーブルを探す
        table = section.find_next("table", {"class": "wikitable"})
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all(["td", "th"])
                if len(cols) >= 3:
                    # 年度, 大賞作品, 著者
                    title = cols[1].get_text(strip=True)
                    author = cols[2].get_text(strip=True)
                    if title and author and "作品" not in title:
                        new_count += save_manga(conn, title, author, "文化庁メディア芸術祭", 0.6)
    return new_count

def main():
    conn = init_db()
    try:
        k_count = fetch_kono_manga(conn)
        print(f"Kono Manga added/updated: {k_count}")
        
        t_count = fetch_manga_taisho(conn)
        print(f"Manga Taisho added: {t_count}")

        m_count = fetch_media_arts(conn)
        print(f"Media Arts added: {m_count}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
