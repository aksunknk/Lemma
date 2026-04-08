import sys
import os
import re
import sqlite3
import urllib.request
import urllib.parse
import json

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\aksak\lemma_project_core\books.db'
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
URLS_TO_TRY = [
    "https://ja.wikipedia.org/wiki/" + urllib.parse.quote("ミリオンセラーの書籍一覧"),
    "https://ja.wikipedia.org/wiki/" + urllib.parse.quote("ミリオンセラー"),
    "https://ja.wikipedia.org/wiki/" + urllib.parse.quote("ベストセラー本の一覧")
]

def fetch_wikipedia_html():
    full_html = ""
    for url in URLS_TO_TRY:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as res:
                full_html += res.read().decode('utf-8')
        except:
            continue
    return full_html

def extract_tables_with_headings(html):
    chunks = re.split(r'(<h[1-6][^>]*>.*?</h[1-6]>)', html, flags=re.IGNORECASE | re.DOTALL)
    active_headings = {i: "" for i in range(1, 7)}
    all_data = []
    
    for chunk in chunks:
        m_h = re.match(r'<h([1-6])', chunk, re.IGNORECASE)
        if m_h:
            level = int(m_h.group(1))
            heading = re.sub(r'<[^>]+>', ' ', chunk).strip()
            active_headings[level] = heading
            for l in range(level + 1, 7):
                active_headings[l] = ""
        else:
            tables_html = re.findall(r'<table[^>]*>(.*?)</table>', chunk, re.DOTALL | re.IGNORECASE)
            for thtml in tables_html:
                rows_html = re.findall(r'<tr[^>]*>(.*?)</tr>', thtml, re.DOTALL | re.IGNORECASE)
                table_data = []
                for rhtml in rows_html:
                    cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', rhtml, re.DOTALL | re.IGNORECASE)
                    clean_cells = []
                    for c in cells:
                        c = re.sub(r'<sup[^>]*>.*?</sup>', '', c, flags=re.DOTALL | re.IGNORECASE)
                        c = re.sub(r'<[^>]+>', ' ', c)
                        c = re.sub(r'\s+', ' ', c).strip()
                        clean_cells.append(c)
                    if clean_cells:
                        table_data.append(clean_cells)
                if table_data:
                    current_heading_text = " ".join([active_headings[l] for l in range(1, 7) if active_headings[l]])
                    all_data.append({'heading': current_heading_text, 'rows': table_data})
    return all_data

def is_foreign_author(name):
    if not name: return False
    if '訳' in name: return True
    clean = re.sub(r'[\s,，.．()（）「」\[\]【】\d０-９:：/／;；]+', '', name)
    katakana = sum(1 for c in clean if '\u30A0' <= c <= '\u30FF' or c == 'ー' or c == '・')
    if len(clean) > 0 and katakana / len(clean) >= 0.5: return True
    return False

def determine_plain_score(title, genre, author, from_wikidata=False):
    text = f"{title} {genre}".lower()
    
    # Literatura prize logic
    if any(aw in text for aw in ['芥川', '直木', '吉川', '三島', 'ノーベル']):
        return 0.2
    
    # Bestseller / Honya Taisho logic
    if any(aw in text for aw in ['本屋大賞', '大賞', '小説', 'エッセイ', 'ノベル', '文庫']):
        return 0.8
        
    if any(hw in text for hw in ['新書', 'ノンフィクション', 'ビジネス', '思想', '実用']):
        return 0.2
        
    if from_wikidata:
        # Default for wikidata broad literature
        return 0.5
        
    return 0.8

def fetch_wikidata_books():
    query = """
    SELECT DISTINCT ?item ?itemLabel ?authorLabel ?pubDate ?awardLabel WHERE {
      { ?item wdt:P31/wdt:P279* wd:Q571. } UNION { ?item wdt:P31/wdt:P279* wd:Q7725634. }
      
      { ?item wdt:P495 wd:Q17. } UNION { ?item wdt:P50 ?author. ?author wdt:P27 wd:Q17. }
      
      ?item rdfs:label ?itemLabel.
      FILTER(LANG(?itemLabel) = "ja")
      
      OPTIONAL { ?item wdt:P50 ?author. ?author rdfs:label ?authorLabel. FILTER(LANG(?authorLabel)="ja") }
      OPTIONAL { ?item wdt:P577 ?pubDate. }
      OPTIONAL { ?item wdt:P166 ?award. ?award rdfs:label ?awardLabel. FILTER(LANG(?awardLabel)="ja") }
      
      ?item wikibase:sitelinks ?sitelinks.
      FILTER(?sitelinks >= 1)
    } ORDER BY DESC(?sitelinks) LIMIT 8000
    """
    
    url = f"{WIKIDATA_ENDPOINT}?query={urllib.parse.quote(query)}&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    books = []
    
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            data = json.loads(res.read().decode('utf-8'))
            for bind in data['results']['bindings']:
                item_url = bind['item']['value']
                q_id = item_url.split('/')[-1]
                title = bind['itemLabel']['value']
                author = bind.get('authorLabel', {}).get('value', '')
                award = bind.get('awardLabel', {}).get('value', '')
                
                year = 0
                pub_date = bind.get('pubDate', {}).get('value', '')
                if pub_date:
                    m = re.search(r'^(\d{4})', pub_date)
                    if m:
                        year = int(m.group(1))
                        
                books.append({
                    'q_id': q_id,
                    'title': title,
                    'author': author,
                    'year': year,
                    'award': award
                })
    except Exception as e:
        print("Wikidata API Error:", e)
        
    return books

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE books ADD COLUMN renown_score REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
        
    # ------------- SOURCE A: Wikipedia Bestsellers -------------
    html = fetch_wikipedia_html()
    tables_obj = extract_tables_with_headings(html)
    books_candidates = []
    
    for t_obj in tables_obj:
        heading = t_obj['heading']
        table_rows = t_obj['rows']
        
        if any(bad in heading for bad in ['シリーズ', 'コミック', '漫画', 'まんが', 'マンガ', 'ゲーム', '音楽', '映画']):
            continue
            
        headers = table_rows[0]
        headers_text = " ".join(headers)
        
        if any(bad in headers_text for bad in ['機種', 'プラットフォーム', '対応機種', 'アーティスト', '発売元', '販売元', 'ハード', 'オリコン', '巻数']):
            continue
            
        if not any(good in headers_text for good in ['書名', 'タイトル']):
            continue
            
        if '作品名' in headers_text:
            continue
            
        for row in table_rows[1:]:
            mapped = {}
            for i, c in enumerate(row):
                if i < len(headers):
                    h = headers[i]
                    if '書名' in h or '作品' in h or 'タイトル' in h: mapped['title'] = c
                    elif '著' in h or '作' in h:
                        if 'author' not in mapped: mapped['author'] = c
                    elif '年' in h: mapped['year'] = c
                    elif '部' in h or '万' in h or '数' in h: mapped['sales'] = c
                    elif 'ジャンル' in h or '備考' in h: mapped['genre'] = c
                        
            if 'title' not in mapped and len(row) >= 4:
                mapped['title'] = row[1] if '1' in row[0] or row[0].isdigit() else row[0]
                mapped['author'] = row[2] if 'title' == row[1] else row[1]
                
            title = mapped.get('title', '')
            if not title: continue
            
            year_str = mapped.get('year', '')
            year_match = re.search(r'([12][0-9]{3})', year_str)
            year = int(year_match.group(1)) if year_match else 0
            if year > 0 and year < 1994:  # 過去30年間 (1994~)
                continue
            
            author = mapped.get('author', '')
            genre = mapped.get('genre', '')
            
            books_candidates.append({
                'source': 'WIKI_BEST',
                'id_base': title,
                'title': title,
                'author': author,
                'year': year,
                'genre': genre
            })

    # ------------- SOURCE B: Wikidata Books -------------
    wiki_data_books = fetch_wikidata_books()
    for b in wiki_data_books:
        # Require year >= 1994 if valid, or accept if 0 (missing metadata but highly linked)
        if b['year'] > 0 and b['year'] < 1994:
            continue
            
        books_candidates.append({
            'source': 'WIKIDATA',
            'id_base': b['q_id'],
            'title': b['title'],
            'author': b['author'],
            'year': b['year'],
            'genre': b['award'] + " " + "WIKIDATA" # embed award to trigger plain_score 0.2 if applicable
        })
            
    # ------------- FILTERING and NOISE REDUCTION -------------
    noise_words = [
        '漫画', 'コミックス', 'コミック', '写真集', '学習参考書', 'タレント本', 
        '攻略本', '辞典', '絵本', 'ゲーム', '図鑑', 'ジャンプ'
    ]
    
    unique_books = {}
    for b in books_candidates:
        title = b['title']
        genre = b.get('genre', '')
        
        text_to_check = f"{title} {genre}".lower()
        if any(w.lower() in text_to_check for w in noise_words):
            continue
            
        # Series check
        if re.search(r'(コミックス|ジャンプ|まんが|コミック|manga|comic)', title, re.IGNORECASE):
            continue
            
        if title not in unique_books:
            unique_books[title] = b
            
    # Process Insertions
    total_added = 0
    all_titles = []
    
    # We want around 3000 items. If we have more, we just take them.
    for b in unique_books.values():
        foreign_score = 1.0 if is_foreign_author(b['author']) else 0.0
        plain_score = determine_plain_score(b['title'], b['genre'], b['author'], from_wikidata=(b['source'] == 'WIKIDATA'))
        
        ncode = f"{b['source']}_{abs(hash(b['id_base'])) % 100000000}"
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO books 
                (id, ncode, title, author, era, foreign_score, plain_score, renown_score, category) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ncode, ncode, b['title'], b['author'], b['year'], foreign_score, plain_score, 1.0, 'RENOWN_MAX'))
            total_added += 1
            all_titles.append(b['title'])
        except sqlite3.Error:
            pass
            
    conn.commit()
    conn.close()
    
    result_path = os.path.join(os.path.dirname(DB_PATH), 'insert_expanded_result.txt')
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(f"{total_added}\n")
        # Write up to 10 sample titles
        for t in all_titles[:10]:
            f.write(f"{t}\n")
            
if __name__ == "__main__":
    main()
