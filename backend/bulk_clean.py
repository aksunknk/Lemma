import sqlite3
import json
import unicodedata
from tqdm import tqdm

DB_PATH = "new_books_2024_2026.db"

def normalize(text):
    return unicodedata.normalize('NFKC', text) if text else "Unknown"

def clean_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cleaned_books (
            isbn TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            publisher TEXT
        )
    """)
    
    cursor.execute("SELECT isbn, raw_json FROM books")
    rows = cursor.fetchall()
    total = len(rows)
    
    batch_size = 1000
    cleaned_batch = []
    
    for isbn, raw_json in tqdm(rows, desc="Cleaning"):
        try:
            data = json.loads(raw_json)
            onix = data.get('onix', {})
            summary = data.get('summary', {})
            
            # Title
            desc_detail = onix.get('DescriptiveDetail', {})
            title_detail = desc_detail.get('TitleDetail', [{}])
            title_detail = title_detail[0] if isinstance(title_detail, list) and title_detail else (title_detail if isinstance(title_detail, dict) else {})
            te = title_detail.get('TitleElement', [{}])
            te = te[0] if isinstance(te, list) and te else (te if isinstance(te, dict) else {})
            title = normalize(te.get('TitleText', {}).get('content') or summary.get('title'))
            
            # Author
            author_raw = "Unknown"
            contribs = desc_detail.get('Contributor', [])
            if isinstance(contribs, list) and contribs:
                author_raw = contribs[0].get('PersonName', {}).get('content')
            elif isinstance(contribs, dict):
                author_raw = contribs.get('PersonName', {}).get('content')
            author = normalize(author_raw or summary.get('author'))
            
            # Publisher
            pub_detail = onix.get('PublishingDetail', {})
            publisher = normalize(pub_detail.get('Imprint', {}).get('ImprintName') or summary.get('publisher'))
            
            cleaned_batch.append((isbn, title, author, publisher))
            
            if len(cleaned_batch) >= batch_size:
                cursor.executemany("INSERT OR IGNORE INTO cleaned_books VALUES (?, ?, ?, ?)", cleaned_batch)
                conn.commit()
                cleaned_batch = []
                
        except Exception:
            continue
            
    if cleaned_batch:
        cursor.executemany("INSERT OR IGNORE INTO cleaned_books VALUES (?, ?, ?, ?)", cleaned_batch)
        conn.commit()
        
    conn.close()
    print(f"\nCompleted: {total} records processed.")

if __name__ == "__main__":
    clean_data()
