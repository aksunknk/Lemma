"""
DB検証スクリプト: 各カテゴリの件数と代表サンプルを出力する
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import func
from database import engine, get_db, Base
from models import Book

Base.metadata.create_all(bind=engine)

def generate_report():
    db = next(get_db())
    
    total = db.query(func.count(Book.id)).scalar()
    print(f"=== DB内の総書籍数: {total} ===\n")
    
    # origin_domestic でカテゴリを大別
    domestic_count = db.query(func.count(Book.id)).filter(Book.origin_domestic == True).scalar()
    foreign_count = db.query(func.count(Book.id)).filter(Book.origin_domestic == False).scalar()
    print(f"国内 (origin_domestic=True): {domestic_count} 冊")
    print(f"海外 (origin_domestic=False): {foreign_count} 冊\n")
    
    # Era分布
    avg_era = db.query(func.avg(Book.era)).scalar()
    min_era = db.query(func.min(Book.era)).scalar()
    max_era = db.query(func.max(Book.era)).scalar()
    print(f"Era: 平均={avg_era:.1f}, 最小={min_era}, 最大={max_era}\n")
    
    # Style分布
    avg_style = db.query(func.avg(Book.style_score)).scalar()
    min_style = db.query(func.min(Book.style_score)).scalar()
    max_style = db.query(func.max(Book.style_score)).scalar()
    print(f"Style: 平均={avg_style:.3f}, 最小={min_style:.3f}, 最大={max_style:.3f}\n")
    
    # Popularity分布
    avg_pop = db.query(func.avg(Book.popularity)).scalar()
    print(f"Popularity: 平均={avg_pop:.3f}\n")
    
    # 各カテゴリから代表1件を抽出
    print("=" * 60)
    print("代表サンプル (各カテゴリ1件ずつ)")
    print("=" * 60)
    
    # カテゴリA: 古い×堅い×国内 → domestic=True, era古い順
    cat_a = db.query(Book).filter(
        Book.origin_domestic == True
    ).order_by(Book.era.asc()).first()
    
    # カテゴリB: 新しい×緩い×国内 → domestic=True, era新しい順, style低い順
    cat_b = db.query(Book).filter(
        Book.origin_domestic == True
    ).order_by(Book.era.desc(), Book.style_score.asc()).first()
    
    # カテゴリC: 堅い×海外 → domestic=False, style高い順
    cat_c = db.query(Book).filter(
        Book.origin_domestic == False
    ).order_by(Book.style_score.desc()).first()
    
    # カテゴリD: 新しい×海外 → domestic=False, era新しい順
    cat_d = db.query(Book).filter(
        Book.origin_domestic == False
    ).order_by(Book.era.desc()).first()
    
    samples = {"A": cat_a, "B": cat_b, "C": cat_c, "D": cat_d}
    labels = {
        "A": "古い×堅い×国内",
        "B": "新しい×緩い×国内",
        "C": "堅い×海外",
        "D": "新しい×海外"
    }
    
    results = {}
    for cat_id, book in samples.items():
        if book:
            print(f"\n--- カテゴリ{cat_id} ({labels[cat_id]}) ---")
            print(f"  タイトル: {book.title}")
            print(f"  著者:     {book.author}")
            print(f"  Era:      {book.era}")
            print(f"  国内:     {book.origin_domestic}")
            print(f"  知名度:   {book.popularity:.3f}")
            print(f"  文体:     {book.style_score:.3f}")
            results[cat_id] = {
                "label": labels[cat_id],
                "title": book.title,
                "author": book.author,
                "era": book.era,
                "origin_domestic": book.origin_domestic,
                "popularity": round(book.popularity, 3),
                "style_score": round(book.style_score, 3)
            }
        else:
            print(f"\n--- カテゴリ{cat_id} ({labels[cat_id]}) --- データなし")
    
    # JSON出力（Artifact用）
    print("\n\n=== JSON出力 ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    
    # 統計情報もJSON出力
    stats = {
        "total": total,
        "domestic": domestic_count,
        "foreign": foreign_count,
        "era_avg": round(avg_era, 1),
        "era_min": min_era,
        "era_max": max_era,
        "style_avg": round(avg_style, 3),
        "pop_avg": round(avg_pop, 3),
    }
    print("\n=== 統計JSON ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    generate_report()
