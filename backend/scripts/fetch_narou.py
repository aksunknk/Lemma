import requests
import json
import time
import sys
import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# アプリケーションルートをパスに追加してmodels/databaseをインポート可能にする
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import Book
from database import SessionLocal, engine, Base

# API Endpoint
NAROU_API_URL = "https://api.syosetu.com/novelapi/api/"

def fetch_narou_data(lim=250, order="hyoka"):
    """
    小説家になろうAPIからデータを取得する
    """
    params = {
        "out": "json",
        "lim": lim,
        "order": order,
        # "gzip": 5 # gzipを外してデバッグしやすくする
    }
    
    try:
        print(f"Fetching data from Narou API (order={order}, lim={lim})...")
        response = requests.get(NAROU_API_URL, params=params, timeout=30)
        
        if response.status_code == 429:
            print("Error: API Rate Limit exceeded. Shutting down safely.")
            sys.exit(1)
        
        response.raise_for_status()
        
        # なろうAPIのJSON出力の1件目はallcount（総件数）なので除外する
        data = response.json()
        if isinstance(data, list) and len(data) > 1:
            return data[1:]
        else:
            print("Error: Unexpected API response format or no data found.")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"Connection Error: {e}")
        print("Shutting down safely.")
        sys.exit(1)

def main():
    # 1. データ取得（メジャー層 + ニッチ層）
    # リクエストA: 総合評価の高い順
    major_data = fetch_narou_data(lim=250, order="hyoka")
    # リクエストB: 新着更新順
    niche_data = fetch_narou_data(lim=250, order="new")
    
    combined_data = major_data + niche_data
    print(f"Total entries fetched: {len(combined_data)}")
    
    if not combined_data:
        print("No data collected. Exiting.")
        return

    # 2. 認知度（NICHE）の正規化のための集計
    global_points = [item.get("global_point", 0) for item in combined_data]
    max_point = max(global_points)
    min_point = min(global_points)
    
    print(f"Global Point Statistics: Max={max_point}, Min={min_point}")
    
    # 3. DB統合
    db = SessionLocal()
    try:
        for item in combined_data:
            ncode = item.get("ncode")
            title = item.get("title")
            writer = item.get("writer")
            story = item.get("story")
            global_point = item.get("global_point", 0)
            firstup = item.get("general_firstup", "2000-01-01 00:00:00")
            
            # 年代抽出
            try:
                era_year = int(firstup[:4])
            except (ValueError, TypeError):
                era_year = 2000
            
            # NICHEスケーリング (最大値 0.0, 最小値 1.0)
            if max_point != min_point:
                popularity = (max_point - global_point) / (max_point - min_point)
            else:
                popularity = 0.5
            
            # DBモデルへのマッピング
            book = db.query(Book).filter(Book.id == ncode).first()
            if not book:
                book = Book(id=ncode)
                db.add(book)
            
            book.title = title
            book.author = writer
            book.description = story
            book.era = era_year
            book.origin_domestic = True # 国内（0.0 -> True as Boolean）
            book.popularity = popularity
            book.style_score = 0.5 # 仮置きの初期値
            book.category = "NAROU"
            
        db.commit()
        print("Database integration completed successfully.")
        
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database Error: {e}")
        print("Rollback performed. Shutting down safely.")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
