import urllib.request
import zipfile
import io
import csv
import sqlite3
import sys
import random

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CSV_URL = "https://www.aozora.gr.jp/index_pages/list_person_all_extended_utf8.zip"
DB_PATH = "books.db"

def main():
    exclude_words = ['年鑑', '白書', 'シラバス', '総目次', '索引']
    
    print("Downloading CSV zip...")
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "LemmaProjectEngine/2.0"})
    with urllib.request.urlopen(req) as res:
        zip_data = res.read()
        
    print("Extracting and processing CSV...")
    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        csv_filename = [name for name in z.namelist() if name.endswith('.csv')][0]
        with z.open(csv_filename) as f:
            text = f.read().decode('utf-8-sig')
            
    reader = csv.DictReader(io.StringIO(text))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Pre-load existing titles to optimize checking
    cursor.execute("SELECT title FROM books")
    existing_titles = {row[0] for row in cursor.fetchall() if row[0]}
    
    count = 0
    new_count = 0
    
    inserted_titles = []
    philosophy_titles = []
    general_titles = []
    
    for row in reader:
        count += 1
        if count % 1000 == 0:
            print(f"進捗: {count}件処理済")
            
        role = row.get("役割フラグ", "")
        if role != "著者":
            continue
            
        ndc = row.get("分類番号", "").strip().replace("NDC ", "")
        
        # NDC filter
        is_hardcore = ndc.startswith("1") or ndc.startswith("3")
        is_lit = ndc.startswith("8") or ndc.startswith("9")
        
        if not (is_hardcore or is_lit):
            continue
            
        title = row.get("作品名", "")
        subtitle = row.get("副題", "")
        full_title = f"{title} {subtitle}"
        
        # Noise filter
        if any(ew in full_title for ew in exclude_words):
            continue
            
        if title in existing_titles:
            continue
            
        book_id = f"aozora-{row.get('作品ID', '0')}"
        author = f"{row.get('姓', '')}{row.get('名', '')}"
        
        orthography = row.get("文字遣い種別", "")
        
        # Scoring
        if is_hardcore:
            style_score = 0.1
        elif is_lit and orthography == "新字新仮名":
            style_score = 0.8
        else:
            style_score = 0.2
            
        birth_date = row.get("生年月日", "")
        era = 1900
        if birth_date and len(birth_date) >= 4 and birth_date[:4].isdigit():
            era = int(birth_date[:4]) + 30 
            
        try:
            cursor.execute("""
                INSERT INTO books (id, title, author, description, era, origin_domestic, popularity, style_score, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (book_id, title, author, subtitle, era, 0.0, 0.8, style_score, "aozora"))
            
            existing_titles.add(title)
            new_count += 1
            inserted_titles.append(title)
            
            if is_hardcore:
                philosophy_titles.append(title)
            else:
                general_titles.append(title)
                
        except sqlite3.IntegrityError:
            pass
            
    conn.commit()
    conn.close()
    
    print(f"NEW_COUNT:{new_count}")
    
    sample_size = min(10, len(inserted_titles))
    samples = []
    
    if philosophy_titles:
        p_samples = random.sample(philosophy_titles, min(3, len(philosophy_titles)))
        samples.extend(p_samples)
        
    remaining = 10 - len(samples)
    if remaining > 0 and general_titles:
        g_samples = random.sample(general_titles, min(remaining, len(general_titles)))
        samples.extend(g_samples)
        
    random.shuffle(samples)
    
    for s in samples:
        print(f"SAMPLE:{s}")

if __name__ == "__main__":
    main()
