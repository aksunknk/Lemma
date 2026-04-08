import sys
import os
import sqlite3
import random
import time
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from database import SessionLocal
    from models import Book
except ImportError:
    pass

OPENBD_COVERAGE_URL = "https://api.openbd.jp/v1/coverage"
OPENBD_GET_URL = "https://api.openbd.jp/v1/get"

MAJOR_PUBLISHERS = ["講談社", "集英社", "新潮社", "KADOKAWA", "文藝春秋", "小学館", "角川"]
HARD_WORDS = ["論証", "体系", "批判", "理性", "形而上学", "哲学", "思想", "定理", "学術", "考察", "理論"]
POSITIVE_WORDS = ["エッセイ", "ユーモア", "日常", "ミステリー", "ファンタジー", "冒険", "青春", "コメディ", "笑い", "エンタメ"]

def is_target_book(data):
    try:
        if not data or not isinstance(data, dict):
            return False
            
        onix = data.get("onix", {})
        summary_obj = data.get("summary", {})
        
        author = summary_obj.get("author", "")
        publisher = summary_obj.get("publisher", "")
        
        c_code = ""
        subjects = onix.get("DescriptiveDetail", {}).get("Subject", [])
        for sub in subjects:
            if sub.get("SubjectSchemeIdentifier") == "78":
                c_code = sub.get("SubjectCode", "")
                break
                
        description = ""
        collateral = onix.get("CollateralDetail", {})
        texts = collateral.get("TextContent", [])
        for t in texts:
            if t.get("TextType") == "03":
                description += t.get("Text", "") + " "
                
        if not description:
            description = data.get("hanmoto", {}).get("hikiai_yomi", "")
            
        if not description:
            description = ""
            
        is_foreign = False
        if "訳" in author:
            is_foreign = True
        if c_code and len(c_code) == 4:
            if c_code[2] == '9' and c_code[3] in ['3', '4', '5', '6', '7', '8', '9']:
                is_foreign = True
                
        if not is_foreign:
            return False
            
        for major in MAJOR_PUBLISHERS:
            if major in publisher:
                return False
                
        if c_code and len(c_code) == 4:
            if c_code[2] in ['1', '2', '3', '4', '5', '6', '8']:
                return False
                
        for hw in HARD_WORDS:
            if hw in description:
                return False
                
        is_plain_entertaining = False
        
        if c_code and len(c_code) == 4:
            if c_code[0] in ['1', '8']:
                is_plain_entertaining = True
                
        for pw in POSITIVE_WORDS:
            if pw in description:
                is_plain_entertaining = True
                break
                
        if not is_plain_entertaining:
            return False
            
        return True
    except Exception:
        return False

def main():
    try:
        resp = requests.get(OPENBD_COVERAGE_URL, timeout=10)
        resp.raise_for_status()
        all_isbns = resp.json()
        
        sample_size = min(500, len(all_isbns))
        sample_isbns = random.sample(all_isbns, sample_size)
        
        books_to_insert = []
        chunk_size = 50
        for i in range(0, len(sample_isbns), chunk_size):
            chunk = sample_isbns[i:i+chunk_size]
            isbn_str = ",".join(chunk)
            
            res = requests.post(OPENBD_GET_URL, data={"isbn": isbn_str}, timeout=20)
            res.raise_for_status()
            books_data = res.json()
            
            for data in books_data:
                if is_target_book(data):
                    books_to_insert.append(data)
                    
            time.sleep(1)
            
        if not books_to_insert:
            return
            
        if 'SessionLocal' in globals():
            db = SessionLocal()
            try:
                for b_data in books_to_insert:
                    summary = b_data.get("summary", {})
                    isbn = summary.get("isbn")
                    title = summary.get("title", "Unknown")
                    author = summary.get("author", "Unknown")
                    
                    description = ""
                    onix = b_data.get("onix", {})
                    texts = onix.get("CollateralDetail", {}).get("TextContent", [])
                    for t in texts:
                        if t.get("TextType") == "03":
                            description += t.get("Text", "") + " "
                    if not description:
                        description = b_data.get("hanmoto", {}).get("hikiai_yomi", "")
                        
                    cover = summary.get("cover", "")
                    
                    existing = db.query(Book).filter(Book.id == f"OPENBD_{isbn}").first()
                    if not existing:
                        new_book = Book(
                            id=f"OPENBD_{isbn}",
                            title=title,
                            author=author,
                            description=description,
                            image_url=cover,
                            era=2024,
                            origin_domestic=False,
                            popularity=0.1,
                            style_score=0.8,
                            category="OPENBD_FOREIGN_PLAIN_NICHE"
                        )
                        db.add(new_book)
                db.commit()
            except Exception as e:
                db.rollback()
                sys.stderr.write(f"DB Error: {str(e)}\n")
            finally:
                db.close()
                
    except Exception as e:
        sys.stderr.write(f"Fetch Error: {str(e)}\n")

if __name__ == "__main__":
    main()
