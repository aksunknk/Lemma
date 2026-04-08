import sys
import os
import re
import time
import random
import sqlite3
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from html import unescape

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\aksak\lemma_project_core\books.db'
SRU_BASE = "https://ndlsearch.ndl.go.jp/api/sru"

GROUPS = {
    'G1': ['ハヤカワ文庫SF', 'ハヤカワ文庫HM', '創元推理文庫', '創元SF文庫', '二見文庫'],
    'G2': ['ハーレクイン', 'MIRA文庫', 'ヴィレッジブックス'],
    'G3': ['ハヤカワ文庫FT', '静山社', '創元ファンタジー'],
    'G4': ['ハヤカワ文庫NV', '文春文庫']
}

def is_foreign_author(name):
    if not name:
        return False
    clean = re.sub(r'[\s,，.．()（）「」\[\]【】\d０-９:：/／;；]+', '', name)
    if not clean:
        return False
    if '・' in name or '＝' in name:
        return True
    
    kanji = sum(1 for c in clean if '\u4e00' <= c <= '\u9fff')
    if kanji >= 2 and '・' not in name:
        return False
        
    katakana = sum(1 for c in clean if '\u30A0' <= c <= '\u30FF' or c in 'ー')
    return len(clean) > 0 and katakana / len(clean) >= 0.6

def clean_title(raw):
    if not raw:
        return ''
    t = raw.strip()
    t = re.sub(r'\s*[\(（【\[]\s*(上|中|下|[0-9０-９]+)\s*[\)）】\]]', '', t)
    t = re.sub(r'\s+第?[0-9０-９]+[巻冊編]$', '', t)
    t = re.sub(r'\s*:\s*(上巻|中巻|下巻|第[0-9０-９]+巻).*$', '', t)
    t = re.sub(r'\s+(上|下|上巻|下巻)$', '', t)
    return t.strip()

def sru_search(query, start_record, max_records=200):
    encoded = urllib.parse.quote(query)
    url = f"{SRU_BASE}?operation=searchRetrieve&maximumRecords={max_records}&startRecord={start_record}&query={encoded}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=60) as res:
        return res.read()

def parse_sru(xml_bytes):
    entries = []
    total = 0
    try:
        root = ET.fromstring(xml_bytes)
    except:
        return entries, total

    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'numberOfRecords' and elem.text:
            try: total = int(elem.text)
            except: pass
            break

    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag != 'recordData':
            continue

        raw_text = ''.join(elem.itertext())
        inner_xml = unescape(raw_text)

        title = ''
        authors = []
        identifier = ''

        for m in re.finditer(r'<dc:title>(.*?)</dc:title>', inner_xml):
            if not title: title = m.group(1).strip()
            
        for m in re.finditer(r'<dc:creator>(.*?)</dc:creator>', inner_xml):
            authors.append(m.group(1).strip())
            
        for m in re.finditer(r'<dc:identifier xsi:type="dcndl:JPNO">(.*?)</dc:identifier>', inner_xml):
            if not identifier: identifier = m.group(1).strip()

        if not identifier:
            for m in re.finditer(r'<dc:identifier(.*?)>(.*?)</dc:identifier>', inner_xml):
                val = m.group(2).strip()
                if not identifier and 'jp' not in val.lower():
                    identifier = val
                    break
                    
        if not identifier and title:
            author_str = "".join(authors)
            identifier = f"GEN_{abs(hash(title + author_str)) % 100000000}"

        if title and identifier:
            entries.append({'title': title, 'authors': authors, 'id': identifier})

    return entries, total

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE books ADD COLUMN ncode TEXT")
        cursor.execute("CREATE UNIQUE INDEX idx_books_ncode ON books(ncode)")
    except sqlite3.OperationalError:
        pass
        
    total_added = 0
    all_added_titles = []
    
    QUOTA_PER_GROUP = 2500
    
    for group_name, labels in GROUPS.items():
        group_added = 0
        quota_per_label = QUOTA_PER_GROUP // len(labels)
        
        for label in labels:
            cql = f'title="{label}"'
            start = 1
            label_added = 0
            empty_streak = 0
            
            while label_added < quota_per_label and group_added < QUOTA_PER_GROUP:
                try:
                    xml_bytes = sru_search(cql, start, max_records=200)
                except Exception as e:
                    print(f"APIエラー {label} (start={start}): {e}")
                    break
                    
                entries, total_results = parse_sru(xml_bytes)
                
                if not entries:
                    empty_streak += 1
                    if empty_streak >= 2: break
                    start += 200
                    time.sleep(2)
                    continue
                    
                empty_streak = 0
                
                for entry in entries:
                    if label_added >= quota_per_label or group_added >= QUOTA_PER_GROUP:
                        break
                        
                    has_foreign = any(is_foreign_author(a) for a in entry['authors'])
                    if not has_foreign:
                        continue
                        
                    t = clean_title(entry['title'])
                    if not t or len(t) < 2:
                        continue
                        
                    ncode = entry['id']
                    
                    try:
                        # ユーザー指定のクエリ＋必須カラムid。IGNOREのせいでNOT NULLなどによる例外が発生しないため確実に指定。
                        cursor.execute("""
                            INSERT OR IGNORE INTO books 
                            (id, ncode, title, foreign_score, plain_score) 
                            VALUES (?, ?, ?, ?, ?)
                        """, (f"NDL_SRU_{ncode}", ncode, t, 1.0, 0.8))
                        
                        if cursor.rowcount > 0:
                            label_added += 1
                            group_added += 1
                            total_added += 1
                            all_added_titles.append(f"[{group_name} / {label}] {t}")
                            
                            if total_added % 1000 == 0:
                                print(f"進捗: {total_added} 件のレコードを処理...")
                    except sqlite3.Error:
                        pass
                
                conn.commit()
                start += 200
                if start > total_results:
                    break
                time.sleep(2)
                
    conn.close()
    
    result_path = os.path.join(os.path.dirname(DB_PATH), 'insert_ndl_result.txt')
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(f"{total_added}\n")
        
        sample_groups = {}
        for item in all_added_titles:
            g = item.split(' / ')[0].strip('[')
            if g not in sample_groups:
                sample_groups[g] = []
            sample_groups[g].append(item)
            
        samples = []
        for g, ts in sample_groups.items():
            k = min(3, len(ts))
            samples.extend(random.sample(ts, k))
            
        final_samples = random.sample(samples, min(10, len(samples)))
        for s in final_samples:
            f.write(f"{s}\n")
            
    print("完了")

if __name__ == "__main__":
    main()
