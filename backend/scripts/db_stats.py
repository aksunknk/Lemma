import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import func

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import engine, get_db
from models import Book

def get_stats():
    db = next(get_db())
    total_count = db.query(func.count(Book.id)).scalar()
    print(f"\n{'='*40}")
    print(f"Total Books in DB: {total_count}")
    print(f"{'='*40}")
    
    ERA_SPLIT = 1945
    
    stats = {
        "A (国内・古典)": db.query(Book).filter(Book.category == "A").count(),
        "B (国内・現代)": db.query(Book).filter(Book.category == "B").count(),
        "C (海外・古典)": db.query(Book).filter(Book.category == "C").count(),
        "D (海外・現代)": db.query(Book).filter(Book.category == "D").count(),
        "WIKI_FOREIGN (Wikipedia海外)": db.query(Book).filter(Book.category == "WIKI_FOREIGN").count(),
        "Unknown": db.query(Book).filter(Book.category == None).count(),
    }
    
    print("\n[Category Distribution]")
    for cat, count in stats.items():
        percentage = (count / total_count * 100) if total_count > 0 else 0
        print(f"  {cat:<15}: {count:>4} 件 ({percentage:5.1f}%)")
    
    # show recent
    print("\n[Recent additions]")
    recent = db.query(Book).order_by(Book.id).limit(5).all() # Actually order by something better if possible
    for b in recent:
        print(f"  {b.id} | {b.title[:30]} | {b.author} | Era:{b.era} | Dom:{b.origin_domestic}")
    print(f"{'='*40}\n")

if __name__ == "__main__":
    get_stats()
