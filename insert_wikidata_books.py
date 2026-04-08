import sys
import os
import re
import time
import random
import sqlite3
import urllib.request
import urllib.parse
import json

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\aksak\lemma_project_core\books.db'
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "lemma_project_bot/1.0 (Contact: local@example.com)"

TARGET_COUNT = 10000
LIMIT = 2000

def fetch_wikidata(offset):
    query = f"""
    SELECT DISTINCT ?item ?itemLabel WHERE {{
      {{ ?item wdt:P31 wd:Q571. }}
      UNION
      {{ ?item wdt:P31 wd:Q7725634. }}
      UNION
      {{ ?item wdt:P31 wd:Q47461344. }}
      
      ?item wdt:P50 ?author.
      MINUS {{ ?author wdt:P27 wd:Q17. }}
      
      ?item rdfs:label ?itemLabel.
      FILTER(LANG(?itemLabel) = "ja")
    }}
    LIMIT {LIMIT} OFFSET {offset}
    """
    
    url = f"{WIKIDATA_ENDPOINT}?query={urllib.parse.quote(query)}&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    
    with urllib.request.urlopen(req, timeout=60) as res:
        data = json.loads(res.read().decode('utf-8'))
        
    return data['results']['bindings']

def clean_title(title):
    t = re.sub(r'\s*\([^)]*\)$', '', title)
    return t.strip()

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE books ADD COLUMN ncode TEXT")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("CREATE UNIQUE INDEX idx_books_ncode ON books(ncode)")
    except sqlite3.OperationalError:
        pass
        
    total_added = 0
    offset = 0
    added_titles = []
    
    while total_added < TARGET_COUNT:
        try:
            bindings = fetch_wikidata(offset)
        except Exception as e:
            print(f"APIリクエスト失敗: {e}")
            break
            
        if not bindings:
            print(f"No more bindings at offset {offset}")
            break
            
        new_in_loop = 0
        for bind in bindings:
            item_url = bind['item']['value']
            q_id = item_url.split('/')[-1]
            raw_title = bind['itemLabel']['value']
            
            title = clean_title(raw_title)
            
            try:
                # 明示的に id カラムを Q識別子 で埋める。これによって NOT NULL 制約を回避
                cursor.execute("""
                    INSERT OR IGNORE INTO books 
                    (id, ncode, title, foreign_score, plain_score, origin_domestic, style_score, category) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (f"WIKI_{q_id}", q_id, title, 1.0, 0.1, 1.0, 0.1, 'WIKIDATA_Q4'))
                
                if cursor.rowcount > 0:
                    total_added += 1
                    new_in_loop += 1
                    added_titles.append(title)
            except sqlite3.Error as e:
                print(f"SQLite DB Error on {q_id} ({title}): {e}")
                
        conn.commit()
        print(f"Offset {offset}: {new_in_loop} 件追加 (累計 {total_added} 件)")
        
        offset += LIMIT
        if len(bindings) < LIMIT or total_added >= TARGET_COUNT:
            break
            
        time.sleep(5)
        
    conn.close()
    
    result_path = os.path.join(os.path.dirname(DB_PATH), 'wikidata_result.txt')
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(f"{total_added}\n")
        if added_titles:
            sample_size = min(10, len(added_titles))
            for t in random.sample(added_titles, sample_size):
                f.write(f"{t}\n")
                
    print("Done")

if __name__ == "__main__":
    main()
