import sqlite3
import json
import unicodedata

def normalize(text):
    return unicodedata.normalize('NFKC', text) if text else ""

def test_parser():
    conn = sqlite3.connect('new_books_2024_2026.db')
    cursor = conn.cursor()
    cursor.execute("SELECT isbn, raw_json FROM books LIMIT 5")
    rows = cursor.fetchall()
    
    print(f"{'ISBN':<15} | {'TITLE':<30} | {'AUTHOR':<20} | {'PUBLISHER'}")
    print("-" * 80)
    
    for isbn, raw_json in rows:
        data = json.loads(raw_json)
        onix = data.get('onix', {})
        summary = data.get('summary', {})
        
        # ONIX 抽出
        desc_detail = onix.get('DescriptiveDetail', {})
        title_detail = desc_detail.get('TitleDetail', [{}])
        if isinstance(title_detail, list) and len(title_detail) > 0:
            title_detail = title_detail[0]
        elif not isinstance(title_detail, list):
            pass # Use as is
        else:
            title_detail = {}
            
        te = title_detail.get('TitleElement', [{}])
        if isinstance(te, list) and len(te) > 0:
            te = te[0]
        elif not isinstance(te, list):
            pass
        else:
            te = {}
            
        title = te.get('TitleText', {}).get('content') or summary.get('title')
        
        # 著者抽出
        author = "Unknown"
        contribs = desc_detail.get('Contributor', [])
        if isinstance(contribs, list) and len(contribs) > 0:
            author = contribs[0].get('PersonName', {}).get('content')
        elif not isinstance(contribs, list):
            author = contribs.get('PersonName', {}).get('content')
        
        if not author:
            author = summary.get('author') or "Unknown"
            
        # 出版社抽出
        pub_detail = onix.get('PublishingDetail', {})
        publisher = pub_detail.get('Imprint', {}).get('ImprintName') or summary.get('publisher')
        
        # 正規化
        n_title = normalize(title)
        n_author = normalize(author)
        n_publisher = normalize(publisher)
        
        print(f"{isbn:<15} | {n_title[:30]:<30} | {n_author[:20]:<20} | {n_publisher}")

    conn.close()

if __name__ == "__main__":
    test_parser()
