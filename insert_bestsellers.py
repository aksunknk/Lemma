import sys
import os
import re
import sqlite3
import urllib.request
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\aksak\lemma_project_core\books.db'
URLS_TO_TRY = [
    "https://ja.wikipedia.org/wiki/" + urllib.parse.quote("ミリオンセラーの書籍一覧"),
    "https://ja.wikipedia.org/wiki/" + urllib.parse.quote("ミリオンセラー"),
    "https://ja.wikipedia.org/wiki/" + urllib.parse.quote("ベストセラー本の一覧")
]

def fetch_html():
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
    # h1-h6の見出しと、それに続くテーブルを紐づける
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
                    all_data.append({
                        'heading': current_heading_text,
                        'rows': table_data
                    })
    return all_data

def is_foreign_author(name):
    if not name: return False
    if '訳' in name: return True
    clean = re.sub(r'[\s,，.．()（）「」\[\]【】\d０-９:：/／;；]+', '', name)
    katakana = sum(1 for c in clean if '\u30A0' <= c <= '\u30FF' or c == 'ー' or c == '・')
    if len(clean) > 0 and katakana / len(clean) >= 0.5: return True
    return False

def determine_scores(title, genre, author):
    foreign_score = 1.0 if is_foreign_author(author) else 0.0
    text = f"{title} {genre}".lower()
    if '小説' in text or 'エッセイ' in text or 'ノベル' in text or '文庫' in text:
        plain_score = 0.8
    elif '新書' in text or 'ノンフィクション' in text or 'ビジネス' in text or '思想' in text or '実用' in text:
        plain_score = 0.2
    else:
        plain_score = 0.5
    return 1.0, foreign_score, plain_score

def parse_sales(sales_str):
    m = re.search(r'([0-9.,]+)(万?)', sales_str)
    if m:
        num = float(m.group(1).replace(',', ''))
        if '万' in sales_str or m.group(2) == '万':
            return num
        elif num >= 100:
            return num / 10000.0  
    return 0.0

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE books ADD COLUMN renown_score REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
        
    html = fetch_html()
    tables_obj = extract_tables_with_headings(html)
    
    books_candidates = []
    
    for t_obj in tables_obj:
        heading = t_obj['heading']
        table_rows = t_obj['rows']
        
        # 爆弾（漫画）が含まれているテーブルは物理的に丸ごとスキップする！！
        if any(bad in heading for bad in ['シリーズ', 'コミック', '漫画', 'まんが', 'マンガ', 'ゲーム', '音楽', '映画']):
            continue
            
        headers = table_rows[0]
        headers_text = " ".join(headers)
        
        if any(bad in headers_text for bad in ['機種', 'プラットフォーム', '対応機種', 'アーティスト', '発売元', '販売元', 'ハード', 'オリコン', '巻数']):
            continue
            
        if not any(good in headers_text for good in ['書名', 'タイトル']):
            continue
            
        # さらに「作品名」がヘッダーにあるテーブル（世界シリーズ本など）は漫画だらけなのでスキップ
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
            if year < 1996: continue
            
            noise_words = ['漫画', 'コミックス', 'コミック', '写真集', '学習参考書', 'タレント本', '攻略本', '辞典', '絵本', 'ゲーム', '図鑑']
            genre = mapped.get('genre', '')
            text_to_check = f"{title} {genre}"
            if any(w in text_to_check for w in noise_words): continue
            
            author = mapped.get('author', '')
            sales = parse_sales(mapped.get('sales', '0'))
            
            if sales > 0:
                books_candidates.append({
                    'title': title, 'author': author, 'year': year, 'sales': sales, 'genre': genre
                })
            
    unique_books = {}
    for b in books_candidates:
        if b['title'] not in unique_books or b['sales'] > unique_books[b['title']]['sales']:
            unique_books[b['title']] = b
            
    sorted_books = sorted(unique_books.values(), key=lambda x: x['sales'], reverse=True)
    top_100 = sorted_books[:100]
    
    total_added = 0
    all_titles = []
    
    for b in top_100:
        renown_score, foreign_score, plain_score = determine_scores(b['title'], b['genre'], b['author'])
        ncode = f"WIKI_BEST_{abs(hash(b['title'] + str(b['year']))) % 100000000}"
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO books 
                (id, ncode, title, author, era, foreign_score, plain_score, renown_score, category) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ncode, ncode, b['title'], b['author'], b['year'], foreign_score, plain_score, renown_score, 'BESTSELLER'))
            total_added += 1
            all_titles.append(b['title'])
        except sqlite3.Error:
            pass
            
    conn.commit()
    conn.close()
    
    result_path = os.path.join(os.path.dirname(DB_PATH), 'insert_bestsellers_result.txt')
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(f"{total_added}\n")
        for t in all_titles[:10]:
            f.write(f"{t}\n")
            
if __name__ == "__main__":
    main()
