import requests
import sqlite3
import time
import re
import random
import os

# 定数
DB_PATH = "google_raw.db"
API_ENDPOINT = "https://www.googleapis.com/books/v1/volumes"

# パブリッシャーリスト (100社以上)
PUBLISHERS = [
    '講談社', '集英社', 'KADOKAWA', '小学館', '文藝春秋', '新潮社', '岩波書店', '光文社', '中央公論新社', '早川書房',
    '東京創元社', '幻冬舎', 'ダイヤモンド社', '東洋経済新報社', '筑摩書房', 'みすず書房', '日経BP', 'SBクリエイティブ',
    'インプレス', '技術評論社', '翔泳社', 'マイナビ出版', 'オーム社', '青土社', '河出書房新社', '平凡社', '晶文社',
    'ポプラ社', '理論社', '福音館書店', 'オーバーラップ', '主婦の友社', '宝島社', 'ぴあ', '昭文社', 'JTBパブリッシング',
    'NHK出版', '有斐閣', '東京大学出版会', '慶應義塾大学出版会', '紀伊國屋書店', '日本評論社', '誠信書房', '医学書院',
    '南江堂', '羊土社', '共立出版', '近代科学社', '裳華房', '朝倉書店', '丸善出版', '白水社', '創元社', '国書刊行会',
    '左右社', '亜紀書房', '扶桑社', '徳間書店', '双葉社', '秋田書店', '白泉社', '芳文社', 'スクウェア・エニックス',
    '竹書房', 'PHP研究所', '大和書房', '秀和システム', 'ラトルズ', 'ボーンデジタル', 'ワークスコーポレーション',
    '誠文堂新光社', '芸術新聞社', '美術出版社', '写大出版', 'フィルムアート社', '太田出版', '彩流社', '柏書房',
    '吉川弘文館', '山川出版社', '雄山閣', '同成社', '勉誠出版', '笠間書院', '八木書店', '明治書院', '東京堂出版',
    '三省堂', '岩崎書店', '金子書房', '培風館', 'サイエンス社', '現代数学社', '数研出版', '旺文社', 'アルク',
    'Z会', '聖文新社', '実業之日本社', '朝日新聞出版', '中経出版', '角川春樹事務所', '祥伝社', 'あかね書房',
    '大修館書店', '福音館書店', 'フレーベル館', '偕成社', 'くもん出版', '福音館', '偕成社', '理論社', '岩崎書店',
    'あすなろ書房', 'ほるぷ出版', '童心社', '金の星社', '小峰書店', '学研プラス', 'マガジンハウス', 'サンマーク出版',
    'PHP文庫', 'SB新書', '講談社現代新書', '中公新書', '岩波新書', '新潮新書'
]
# 重複排除
PUBLISHERS = list(set(PUBLISHERS))

# ベクトル化用キーワード
HARD_KEYWORDS = ['論', '考', '研究', '史', '哲学', '社会', '思想', '構造', '経済', '政治', '理論', '技術', '科学']
SOFT_KEYWORDS = ['異世界', '転生', '魔法', '少女', '恋', 'ちゃん', 'ダンジョン', 'ラブコメ', 'ふあふあ', 'まったり', 'ほのぼの' ]
MAJOR_PUBLISHERS = ['講談社', '集英社', 'KADOKAWA', '小学館', '文藝春秋', '新潮社', '学研', 'ポプラ社', '岩波書店', '筑摩書房']

def clamp(n, minn=0.0, maxn=1.0):
    return max(min(maxn, n), minn)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            isbn TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            publisher TEXT,
            pubdate TEXT,
            description TEXT,
            era REAL,
            origin REAL,
            style REAL,
            renown REAL
        )
    """)
    conn.commit()
    return conn

def calculate_heuristics(title, author, publisher, description, pubdate, categories):
    # 1. ERA
    year = 2020
    if pubdate:
        match = re.search(r'\d{4}', pubdate)
        if match: year = int(match.group(0))
    era = (year - 1800) / (2030 - 1800)
    
    # 2. ORIGIN
    origin = 0.0
    if author and any(char in author for char in ['・', '=', '訳']):
        origin = 1.0
        
    # 3. STYLE (あらすじが無い場合は title と categories を優先)
    style = 0.5
    text_for_style = (title or "") + (description or "") + (" ".join(categories or []))
    for k in HARD_KEYWORDS:
        if k in text_for_style: style += 0.2
    for k in SOFT_KEYWORDS:
        if k in text_for_style: style -= 0.2
    
    # カテゴリによる補正
    if categories:
        cat_text = " ".join(categories).lower()
        if any(w in cat_text for w in ['fiction', 'juvenile', 'comic', 'novel']):
            style -= 0.1
        if any(w in cat_text for w in ['science', 'philosophy', 'history', 'business', 'law', 'education']):
            style += 0.2
            
    style = clamp(style)
    
    # 4. RENOWN
    renown = 0.3
    if publisher and any(p in publisher for p in MAJOR_PUBLISHERS):
        renown += 0.3
    if description and len(description) > 300:
        renown += 0.3
    if not description: # あらすじ無しは知名度低めに見積もる
        renown -= 0.1
        
    renown = clamp(renown)
    
    # Noise
    era = clamp(era + random.uniform(-0.02, 0.02))
    origin = clamp(origin + random.uniform(-0.02, 0.02))
    style = clamp(style + random.uniform(-0.02, 0.02))
    renown = clamp(renown + random.uniform(-0.02, 0.02))
    
    return era, origin, style, renown

def fetch_google_books():
    conn = init_db()
    cursor = conn.cursor()
    
    total_added = 0
    total_requested = len(PUBLISHERS) * 1000
    
    print(f"Starting Maximal Fetch Strategy for {len(PUBLISHERS)} publishers.")

    for pub in PUBLISHERS:
        print(f"[{time.strftime('%H:%M:%S')}] Target: {pub} | Current Total: {total_added}")
        
        sleep_wait = 1.0
        
        for start_index in range(0, 1000, 40):
            params = {
                'q': f'inpublisher:{pub}',
                'langRestrict': 'ja',
                'startIndex': start_index,
                'maxResults': 40,
                'orderBy': 'newest'
            }
            
            retry_count = 0
            while retry_count < 5:
                try:
                    res = requests.get(API_ENDPOINT, params=params, timeout=15)
                    
                    if res.status_code == 200:
                        data = res.json()
                        items = data.get('items', [])
                        if not items: break
                        
                        for item in items:
                            vol = item.get('volumeInfo', {})
                            title = vol.get('title', '')
                            # あらすじが空でもタイトルにひらがながあればOK
                            description = vol.get('description', '')
                            combined_text = title + (description or "")
                            
                            if not re.search(r'[\u3040-\u309F]', combined_text):
                                continue

                            authors = vol.get('authors', [])
                            author = authors[0] if authors else ""
                            pub_name = vol.get('publisher', '')
                            pubdate = vol.get('publishedDate', '') or ""
                            categories = vol.get('categories', [])
                            
                            isbns = vol.get('industryIdentifiers', [])
                            isbn = None
                            for id_item in isbns:
                                if id_item.get('type') in ['ISBN_13', 'ISBN_10']:
                                    isbn = id_item.get('identifier')
                                    break
                            
                            if isbn:
                                era, origin, style, renown = calculate_heuristics(title, author, pub_name, description, pubdate, categories)
                                try:
                                    cursor.execute("""
                                        INSERT OR IGNORE INTO books (isbn, title, author, publisher, pubdate, description, era, origin, style, renown)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (isbn, title, author, pub_name, pubdate, description, era, origin, style, renown))
                                    if cursor.rowcount > 0:
                                        total_added += 1
                                except: pass
                        
                        conn.commit()
                        time.sleep(sleep_wait)
                        break # Success, next startIndex
                        
                    elif res.status_code == 429 or res.status_code == 503:
                        wait = sleep_wait * (2 ** retry_count)
                        print(f"Status {res.status_code}. Backing off: {wait}s...")
                        time.sleep(wait)
                        retry_count += 1
                    else:
                        print(f"API Error: {res.status_code}")
                        break
                        
                except Exception as e:
                    print(f"Request Error: {e}")
                    time.sleep(5)
                    retry_count += 1
            
            if retry_count >= 5: break

    conn.close()
    print(f"Finished. Total unique books added: {total_added}")

if __name__ == "__main__":
    fetch_google_books()
