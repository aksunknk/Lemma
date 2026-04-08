import argparse
import sys
import os
import time
import requests
from sqlalchemy.orm import Session
from sqlalchemy import func
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

# Add backend directory to module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import engine, get_db, Base
from models import Book
from services.text_analysis import calculate_style_score

Base.metadata.create_all(bind=engine)

# --- ハイブリッドクエリ配列 ---
CATEGORIES = {
    "A": {
        "name": "古い・堅い・国内",
        "queries": [
            'subject:"Japanese fiction" 古典',
            '日本文学 名作',
            '純文学',
            '夏目漱石',
            '芥川龍之介',
        ],
        "domestic": True,
        "fallback_era": 1910,
    },
    "B": {
        "name": "新しい・緩い・国内",
        "queries": [
            'ライトノベル',
            'エンターテインメント 小説',
            'subject:"Fiction / Fantasy / General"',
            '電撃文庫',
        ],
        "domestic": True,
        "fallback_era": 2015,
    },
    "C": {
        "name": "堅い・海外",
        "queries": [
            'subject:"Philosophy"',
            '西洋哲学 翻訳',
            'カント',
            'ヘーゲル',
        ],
        "domestic": False,
        "fallback_era": 1880,
    },
    "D": {
        "name": "新しい・海外",
        "queries": [
            'subject:"Science Fiction" 翻訳',
            '海外SF 名作',
            'ヒューゴー賞 翻訳',
            'スペースオペラ',
        ],
        "domestic": False,
        "fallback_era": 2010,
    },
}

TARGET_PER_CATEGORY = 125
MAX_RESULTS = 40  # Google Books API max per page


def fetch_books_for_query(query: str, start_index: int) -> dict | None:
    """Google Books API から1ページ分を取得。レートリミット時はリトライ。"""
    url = (
        f"https://www.googleapis.com/books/v1/volumes"
        f"?q={query}&startIndex={start_index}&maxResults={MAX_RESULTS}&langRestrict=ja"
    )
    if API_KEY:
        url += f"&key={API_KEY}"

    for attempt in range(5):
        try:
            resp = requests.get(url, timeout=15)
        except requests.exceptions.RequestException as e:
            print(f"    ネットワークエラー: {e}")
            time.sleep(10)
            continue

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"    429 Rate Limit — {wait}秒待機... (attempt {attempt+1}/5)")
            time.sleep(wait)
            continue
        else:
            print(f"    APIエラー ({resp.status_code})")
            return None

    return None


def process_item(item: dict, cat_id: str, cat_info: dict, db: Session) -> dict | None:
    """1件の volumeInfo を処理し、DBに保存。成功すれば sample dict を返す。"""
    v_info = item.get("volumeInfo", {})
    vid = item.get("id")

    desc = v_info.get("description", "")
    lang = v_info.get("language", "")

    # フィルタ: あらすじなし or 日本語以外
    if not desc or lang != "ja":
        return None

    # 重複チェック
    if db.query(Book).filter(Book.id == vid).first():
        return None

    title = v_info.get("title", "Unknown")
    authors = v_info.get("authors", ["Unknown"])
    image_links = v_info.get("imageLinks", {})
    image_url = image_links.get("thumbnail", "")

    # --- 4軸スコア算出 ---
    style = calculate_style_score(desc)

    ratings_count = v_info.get("ratingsCount", 0)
    popularity = min(1.0, ratings_count / 100.0)
    if popularity == 0:
        page_count = v_info.get("pageCount", 0)
        popularity = min(1.0, float(page_count) / 500.0)

    pub_date = v_info.get("publishedDate", "")
    era = cat_info["fallback_era"]
    if pub_date:
        parts = pub_date.split("-")
        if parts and parts[0].isdigit():
            era = int(parts[0])

    domestic = cat_info["domestic"]

    book = Book(
        id=vid,
        title=title,
        author=authors[0],
        description=desc,
        image_url=image_url,
        era=era,
        origin_domestic=domestic,
        popularity=popularity,
        style_score=style,
        category=cat_id,
    )
    db.add(book)
    db.commit()

    return {
        "title": title,
        "author": book.author,
        "era": era,
        "origin_domestic": domestic,
        "popularity": round(popularity, 3),
        "style_score": round(style, 3),
    }


def run_seed(resume=False):
    db = next(get_db())

    if resume:
        print("Resumeモードが有効です。既存データを保持します。")
    else:
        # 既存データを全削除して再蓄積
        deleted = db.query(Book).delete()
        db.commit()
        print(f"既存レコード {deleted} 件を削除しました。\n")

    report_samples = {}
    grand_total = 0

    for cat_id, cat_info in CATEGORIES.items():
        print(f"=== カテゴリ {cat_id}: {cat_info['name']} ===")
        
        # 既存件数を正確に取得 (Resume時)
        if resume:
            saved_count = db.query(Book).filter(Book.category == cat_id).count()
            print(f"  現在のDB内件数: {saved_count} 件")
        else:
            saved_count = 0
            
        seen_ids = set()
        
        # 目標に達している場合はスキップ
        if saved_count >= TARGET_PER_CATEGORY:
            print(f"  カテゴリ {cat_id} は既に目標数に達しているためスキップします。")
            grand_total += saved_count
            continue

        # 各クエリをローテーション
        for qi, query in enumerate(cat_info["queries"]):
            if saved_count >= TARGET_PER_CATEGORY:
                break

            per_query_target = max(
                10,
                (TARGET_PER_CATEGORY - saved_count)
                // (len(cat_info["queries"]) - qi),
            )
            print(f"  [{qi+1}/{len(cat_info['queries'])}] q=\"{query}\" (不足分目標: {per_query_target}件)")

            start_index = 0
            query_saved = 0

            while query_saved < per_query_target and saved_count < TARGET_PER_CATEGORY:
                data = fetch_books_for_query(query, start_index)
                if not data:
                    break

                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    if saved_count >= TARGET_PER_CATEGORY:
                        break

                    vid = item.get("id")
                    if vid in seen_ids:
                        continue
                    seen_ids.add(vid)

                    sample = process_item(item, cat_id, cat_info, db)
                    if sample:
                        saved_count += 1
                        query_saved += 1

                        # 代表サンプルを保存 (最初の1件)
                        if cat_id not in report_samples:
                            report_samples[cat_id] = sample

                start_index += MAX_RESULTS
                time.sleep(2)  # レートリミット配慮（2秒間隔）

            print(f"    → このクエリで {query_saved} 件保存 (計 {saved_count}/{TARGET_PER_CATEGORY})")

        grand_total += saved_count
        print(f"  カテゴリ {cat_id} 完了: {saved_count} 件\n")

    print(f"\n{'='*50}")
    print(f"全カテゴリ合計: {grand_total} 件")
    print(f"{'='*50}")
    print("\n--- 代表サンプル ---")
    for cat_id, sample in report_samples.items():
        print(f"\nカテゴリ {cat_id} ({CATEGORIES[cat_id]['name']}):")
        print(f"  タイトル : {sample['title']}")
        print(f"  著者     : {sample['author']}")
        print(f"  Era      : {sample['era']}")
        print(f"  Domestic : {sample['origin_domestic']}")
        print(f"  Popularity: {sample['popularity']}")
        print(f"  Style    : {sample['style_score']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", help="既存データを削除せずに収集を再開する")
    args = parser.parse_args()
    
    run_seed(resume=args.resume)
