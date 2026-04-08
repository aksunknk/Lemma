import sys
import os
import io
import re
import csv
import time
import random
import sqlite3
import zipfile
import urllib.request
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\aksak\lemma_project_core\books.db'

# ── ユーティリティ ──────────────────────────────────────────

def is_katakana_dominant(text):
    """文字列がカタカナ主体かどうか判定"""
    if not text:
        return False
    katakana = sum(1 for c in text if '\u30A0' <= c <= '\u30FF')
    total = sum(1 for c in text if not c.isspace() and c not in '・=＝()（）「」,、.。')
    return total > 0 and (katakana / total) >= 0.5


def is_foreign_author(author_name):
    """著者名が外国人かどうかを判定"""
    if not author_name:
        return False
    # 「, 」で分割された「姓, 名」形式の処理
    name = author_name.replace(',', '').replace('，', '').strip()
    if '・' in name:
        return True
    if is_katakana_dominant(name):
        return True
    return False


def clean_title(raw_title):
    """タイトルから巻数表記・サブタイトルをクリーンにする"""
    if not raw_title:
        return raw_title
    t = raw_title.strip()
    t = re.sub(r'\s*[\(（【\[]\s*(上|中|下|[0-9０-９]+)\s*[\)）】\]]', '', t)
    t = re.sub(r'\s+第?[0-9０-９]+[巻冊編]$', '', t)
    t = re.sub(r'\s*:\s*(上巻|中巻|下巻|第[0-9０-９]+巻).*$', '', t)
    t = t.strip()
    return t


# ── フェーズ1: 青空文庫データの国籍サルベージ ─────────────────

def phase1_aozora_salvage(conn):
    print("【フェーズ1】青空文庫CSVダウンロード中...")
    url = "https://www.aozora.gr.jp/index_pages/list_person_all_extended_utf8.zip"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    })
    with urllib.request.urlopen(req, timeout=60) as res:
        zip_data = res.read()

    zf = zipfile.ZipFile(io.BytesIO(zip_data))
    csv_name = [n for n in zf.namelist() if n.endswith('.csv')][0]
    csv_bytes = zf.read(csv_name)
    csv_text = csv_bytes.decode('utf-8')

    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader)

    col_map = {h: i for i, h in enumerate(header)}
    print(f"  CSVカラム数: {len(header)}")
    print(f"  先頭カラム: {header[:6]}")

    # 青空文庫拡張CSVの主要カラム
    title_idx = col_map.get('作品名', 1)
    lastname_idx = col_map.get('姓', None)
    firstname_idx = col_map.get('名', None)
    role_idx = col_map.get('役割フラグ', None)

    # カラム名が見つからない場合、ヘッダーを調べて推測
    if lastname_idx is None:
        for h, i in col_map.items():
            if '姓' in h and '読み' not in h:
                lastname_idx = i
                break
    if firstname_idx is None:
        for h, i in col_map.items():
            if '名' == h or ('名' in h and '読み' not in h and '作品' not in h):
                firstname_idx = i
                break
    if role_idx is None:
        for h, i in col_map.items():
            if '役割' in h:
                role_idx = i
                break

    print(f"  title_idx={title_idx}, lastname_idx={lastname_idx}, firstname_idx={firstname_idx}, role_idx={role_idx}")

    translator_titles = set()
    foreign_author_titles = set()

    reader2 = csv.reader(io.StringIO(csv_text))
    next(reader2)

    for row in reader2:
        max_needed = max(x for x in [title_idx, lastname_idx, firstname_idx, role_idx] if x is not None)
        if len(row) <= max_needed:
            continue

        title = row[title_idx].strip()
        last_name = row[lastname_idx].strip() if lastname_idx is not None else ''
        first_name = row[firstname_idx].strip() if firstname_idx is not None else ''
        full_name = last_name + first_name
        role = row[role_idx].strip() if role_idx is not None else ''

        if not title:
            continue

        if '翻訳' in role or '訳者' in role:
            translator_titles.add(title)

        if ('著者' in role or role == '') and '・' in full_name:
            foreign_author_titles.add(title)

    foreign_titles = translator_titles | foreign_author_titles
    print(f"  海外作品候補: {len(foreign_titles)} 件")

    cursor = conn.cursor()
    updated = 0
    for title in foreign_titles:
        cursor.execute("""
            UPDATE books SET origin_domestic = 1.0
            WHERE title = ? AND origin_domestic < 0.5
        """, (title,))
        updated += cursor.rowcount

    conn.commit()
    print(f"  DB更新完了: {updated} 件")
    return updated


# ── フェーズ2: 国立国会図書館API + タイトル直接検索 ──────────

KNOWN_FOREIGN_AUTHORS = [
    "ドストエフスキー", "トルストイ", "チェーホフ", "ゴーゴリ",
    "シェイクスピア", "ディケンズ", "オースティン", "ブロンテ",
    "カフカ", "ゲーテ", "ヘッセ", "トーマス・マン", "ニーチェ",
    "カミュ", "サルトル", "フローベール", "バルザック", "ユゴー", "スタンダール", "モーパッサン", "プルースト", "ゾラ",
    "ヘミングウェイ", "フィッツジェラルド", "フォークナー", "メルヴィル", "ポー",
    "マルケス", "ボルヘス",
    "ダンテ", "ボッカッチョ",
    "セルバンテス",
    "プラトン", "アリストテレス", "ホメロス",
    "魯迅",
    "カント", "ヘーゲル", "ショーペンハウアー", "ウィトゲンシュタイン",
    "フロイト", "ユング",
    "マキャヴェリ", "モンテスキュー", "ルソー", "ホッブズ", "ロック",
    "アダム・スミス", "マルクス", "ウェーバー",
    "ダーウィン",
    "チョーサー", "ミルトン", "ワーズワース", "バイロン",
    "ドイル", "アガサ・クリスティー",
    "オーウェル", "ハクスリー",
    "ソルジェニーツィン", "ツルゲーネフ", "ブルガーコフ",
    "トーマス・ハーディ", "ジョイス", "ベケット",
    "サン＝テグジュペリ", "モリエール", "ラシーヌ",
]

KNOWN_WORKS = [
    "罪と罰", "カラマーゾフの兄弟", "白痴", "悪霊", "地下室の手記",
    "戦争と平和", "アンナ・カレーニナ", "復活",
    "変身", "城", "審判",
    "ファウスト", "若きウェルテルの悩み",
    "車輪の下", "デミアン", "荒野のおおかみ",
    "異邦人", "ペスト", "シーシュポスの神話",
    "嘔吐", "存在と無",
    "ボヴァリー夫人", "感情教育",
    "失われた時を求めて", "居酒屋",
    "レ・ミゼラブル", "赤と黒",
    "ハムレット", "リア王", "オセロー", "マクベス",
    "老人と海", "武器よさらば", "誰がために鐘は鳴る",
    "グレート・ギャツビー",
    "白鯨",
    "百年の孤独",
    "神曲", "デカメロン", "ドン・キホーテ",
    "イリアス", "オデュッセイア",
    "国家", "ニコマコス倫理学", "形而上学",
    "純粋理性批判", "実践理性批判", "判断力批判",
    "精神現象学", "法の哲学",
    "意志と表象としての世界",
    "論理哲学論考",
    "夢判断", "精神分析入門",
    "君主論", "法の精神", "社会契約論", "リヴァイアサン",
    "国富論", "資本論", "プロテスタンティズムの倫理と資本主義の精神",
    "種の起源",
    "カンタベリー物語", "失楽園",
    "シャーロック・ホームズ",
    "一九八四年", "すばらしい新世界",
    "収容所群島", "父と子",
    "ユリシーズ", "ゴドーを待ちながら",
    "星の王子さま",
]


def fetch_ndl_xml(params_str):
    """NDL OpenSearch APIからXMLを取得"""
    from urllib.parse import quote
    url = f"https://ndlsearch.ndl.go.jp/api/opensearch?{params_str}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    })
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def parse_rss_items(xml_bytes):
    """RSS XMLをパースしてアイテムのリストを返す"""
    entries = []
    total_results = 0

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return entries, total_results

    # totalResults
    for elem in root.iter():
        if 'totalResults' in elem.tag:
            try:
                total_results = int(elem.text)
            except (ValueError, TypeError):
                pass
            break

    # itemを探索（名前空間対応）
    items = []
    for elem in root.iter():
        if elem.tag.endswith('}item') or elem.tag == 'item':
            items.append(elem)

    for item in items:
        title = ''
        authors = []
        description = ''
        publisher = ''

        for child in item:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            if tag == 'title' and child.text:
                title = child.text.strip()
            elif tag == 'creator' and child.text:
                authors.append(child.text.strip())
            elif tag == 'author' and child.text:
                authors.append(child.text.strip())
            elif tag == 'description' and child.text:
                description = child.text.strip()
            elif tag == 'publisher' and child.text:
                publisher = child.text.strip()

        if title:
            entries.append({
                'title': title,
                'authors': authors,
                'description': description,
                'publisher': publisher,
            })

    return entries, total_results


def phase2_ndl_fetch(conn):
    cursor = conn.cursor()
    total_inserted = 0
    all_inserted_titles = []

    # ── 戦略A: シリーズ名でページネーション ──
    series_list = ['岩波文庫', '光文社古典新訳文庫', '中公クラシックス', 'ちくま学芸文庫']

    for series in series_list:
        print(f"\n【フェーズ2-A】NDLシリーズ検索: {series}")
        idx = 1
        series_inserted = 0
        max_pages = 50

        for page in range(max_pages):
            from urllib.parse import quote
            params = f"series={quote(series)}&cnt=100&idx={idx}"

            try:
                xml_bytes = fetch_ndl_xml(params)
            except Exception as e:
                print(f"  APIエラー (idx={idx}): {e}")
                break

            entries, total_results = parse_rss_items(xml_bytes)

            if not entries:
                break

            for entry in entries:
                authors = entry['authors']
                title_raw = entry['title']

                has_foreign = any(is_foreign_author(a) for a in authors)
                if not has_foreign:
                    continue

                title = clean_title(title_raw)
                if not title or len(title) < 2:
                    continue

                author_str = ', '.join(authors)

                cursor.execute("SELECT 1 FROM books WHERE title = ?", (title,))
                if cursor.fetchone():
                    continue

                book_id = f"NDL_S_{abs(hash(title + series)) % 10000000}"

                cursor.execute("""
                    INSERT OR IGNORE INTO books
                    (id, title, author, description, era, origin_domestic, popularity, style_score, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (book_id, title, author_str, entry.get('description', ''),
                      2000, 1.0, 0.1, 0.1, 'NDL_Q4'))

                if cursor.rowcount > 0:
                    series_inserted += 1
                    all_inserted_titles.append(title)

            conn.commit()
            print(f"  idx={idx}: 取得{len(entries)}件 / 新規{series_inserted}件 (total={total_results})")

            idx += 100
            if total_results > 0 and idx > min(total_results, 5000):
                break

            time.sleep(2)

        total_inserted += series_inserted
        print(f"  {series} 完了: {series_inserted} 件")

    # ── 戦略B: 著名な海外著者名で直接検索 ──
    print(f"\n【フェーズ2-B】著名海外著者の直接検索")
    for author_name in KNOWN_FOREIGN_AUTHORS:
        from urllib.parse import quote
        params = f"creator={quote(author_name)}&cnt=100&idx=1"

        try:
            xml_bytes = fetch_ndl_xml(params)
        except Exception as e:
            time.sleep(2)
            continue

        entries, _ = parse_rss_items(xml_bytes)
        author_added = 0

        for entry in entries:
            title = clean_title(entry['title'])
            if not title or len(title) < 2:
                continue

            author_str = ', '.join(entry['authors']) if entry['authors'] else author_name

            cursor.execute("SELECT 1 FROM books WHERE title = ?", (title,))
            if cursor.fetchone():
                continue

            book_id = f"NDL_A_{abs(hash(title + author_name)) % 10000000}"

            cursor.execute("""
                INSERT OR IGNORE INTO books
                (id, title, author, description, era, origin_domestic, popularity, style_score, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (book_id, title, author_str, entry.get('description', ''),
                  2000, 1.0, 0.1, 0.1, 'NDL_Q4'))

            if cursor.rowcount > 0:
                author_added += 1
                total_inserted += 1
                all_inserted_titles.append(title)

        conn.commit()
        if author_added > 0:
            print(f"  {author_name}: +{author_added}件")
        time.sleep(2)

    # ── 戦略C: 著名作品タイトルで直接検索 ──
    print(f"\n【フェーズ2-C】著名海外作品の直接検索")
    for work_title in KNOWN_WORKS:
        from urllib.parse import quote
        params = f"title={quote(work_title)}&cnt=10&idx=1"

        try:
            xml_bytes = fetch_ndl_xml(params)
        except Exception as e:
            time.sleep(2)
            continue

        entries, _ = parse_rss_items(xml_bytes)

        for entry in entries:
            title = clean_title(entry['title'])
            if not title or len(title) < 2:
                continue

            # タイトルがあまりに一致しない場合スキップ
            if work_title not in title and title not in work_title:
                continue

            author_str = ', '.join(entry['authors']) if entry['authors'] else ''

            cursor.execute("SELECT 1 FROM books WHERE title = ?", (title,))
            if cursor.fetchone():
                continue

            book_id = f"NDL_W_{abs(hash(title)) % 10000000}"

            cursor.execute("""
                INSERT OR IGNORE INTO books
                (id, title, author, description, era, origin_domestic, popularity, style_score, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (book_id, title, author_str, entry.get('description', ''),
                  2000, 1.0, 0.1, 0.1, 'NDL_Q4'))

            if cursor.rowcount > 0:
                total_inserted += 1
                all_inserted_titles.append(title)

        conn.commit()
        time.sleep(2)

    print(f"\nフェーズ2合計: 新規追加 {total_inserted} 件")
    return total_inserted, all_inserted_titles


# ── メイン ──────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB_PATH)

    updated_count = phase1_aozora_salvage(conn)
    inserted_count, inserted_titles = phase2_ndl_fetch(conn)

    conn.close()

    result_path = os.path.join(os.path.dirname(DB_PATH), 'q4_augment_result.txt')
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(f"【フェーズ1】青空文庫データから海外作品として修復（UPDATE）された件数: {updated_count} 件\n")
        f.write(f"【フェーズ2】国立国会図書館APIから新規追加（INSERT）された総件数: {inserted_count} 件\n\n")
        f.write("フェーズ2で登録されたタイトルのサンプル（ランダム10件）:\n")
        if inserted_titles:
            sample_size = min(10, len(inserted_titles))
            for t in random.sample(inserted_titles, sample_size):
                f.write(f"  - {t}\n")
        f.write(f"\n全登録タイトル一覧 ({len(inserted_titles)}件):\n")
        for t in inserted_titles:
            f.write(f"  - {t}\n")

    print(f"\n=== 最終結果 ===")
    print(f"【フェーズ1】修復件数: {updated_count} 件")
    print(f"【フェーズ2】新規追加件数: {inserted_count} 件")
    print(f"結果ファイル: {result_path}")


if __name__ == "__main__":
    main()
