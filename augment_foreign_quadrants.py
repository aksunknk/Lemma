import sys
import os
import re
import time
import random
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import quote

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\aksak\lemma_project_core\books.db'
SRU_BASE = "https://ndlsearch.ndl.go.jp/api/sru"

# ── ターゲット著者リスト ────────────────────────────────────

Q1_AUTHORS = [
    "アイザック・アシモフ", "アーサー・C・クラーク", "フィリップ・K・ディック",
    "ロバート・A・ハインライン", "レイ・ブラッドベリ", "ウィリアム・ギブスン",
    "アーシュラ・K・ル・グィン", "H・G・ウェルズ", "ジュール・ヴェルヌ",
    "カート・ヴォネガット", "スタニスワフ・レム", "テッド・チャン",
    "ダグラス・アダムズ",
    "アガサ・クリスティー", "レイモンド・チャンドラー", "ダシール・ハメット",
    "エラリー・クイーン", "ジョン・ル・カレ", "パトリシア・コーンウェル",
    "マイクル・コナリー", "リー・チャイルド", "ジェフリー・ディーヴァー",
    "スティーグ・ラーソン", "ドン・ウィンズロウ", "デニス・ルヘイン",
    "トマス・ハリス", "ジェイムズ・エルロイ",
    "コナン・ドイル", "モーリス・ルブラン", "ガストン・ルルー",
    "ジョルジュ・シムノン", "エド・マクベイン",
    "スティーヴン・キング", "H・P・ラヴクラフト",
    "J・R・R・トールキン", "C・S・ルイス",
    "ニール・ゲイマン", "ジョージ・R・R・マーティン",
    "シドニィ・シェルダン", "ジョン・グリシャム",
    "マイケル・クライトン", "ダン・ブラウン", "ケン・フォレット",
    "ジェフリー・アーチャー", "トム・クランシー",
    "フレデリック・フォーサイス",
    "アレクサンドル・デュマ", "ロバート・L・スティーヴンソン",
    "ジャック・ロンドン", "マーク・トウェイン", "ルイス・キャロル",
    "クリスティアナ・ブランド", "ロアルド・ダール",
    "ディーン・クーンツ", "ジェイムズ・パタースン",
    "アン・ライス", "ロビン・クック",
]

Q4_AUTHORS = [
    "ドストエフスキー", "トルストイ", "チェーホフ", "ゴーゴリ",
    "ツルゲーネフ", "ソルジェニーツィン", "ナボコフ", "プーシキン",
    "カフカ", "ゲーテ", "ヘッセ", "トーマス・マン", "ブレヒト",
    "リルケ", "ハインリヒ・ベル",
    "カミュ", "サルトル", "フローベール", "バルザック", "スタンダール",
    "モーパッサン", "プルースト", "ゾラ", "ジッド", "モリエール",
    "ボードレール", "ランボー", "サン＝テグジュペリ",
    "シェイクスピア", "ディケンズ", "ジョイス",
    "ヴァージニア・ウルフ", "D・H・ロレンス", "ジョセフ・コンラッド",
    "ヘミングウェイ", "フィッツジェラルド", "フォークナー", "メルヴィル",
    "ポー", "ヘンリー・ジェイムズ", "トニ・モリスン",
    "マルケス", "ボルヘス", "バルガス・リョサ",
    "プラトン", "アリストテレス", "カント", "ヘーゲル",
    "ショーペンハウアー", "ニーチェ", "ウィトゲンシュタイン",
    "ハイデガー", "フッサール", "デリダ", "フーコー", "ドゥルーズ",
    "ホメロス", "ダンテ", "セルバンテス",
    "モンテーニュ", "パスカル",
    "マキャヴェリ", "ホッブズ", "ロック", "ルソー", "モンテスキュー",
    "アダム・スミス", "マルクス", "ウェーバー", "フロイト", "ユング",
    "ハンナ・アーレント", "ダーウィン",
    "ベケット", "オーウェル", "イプセン",
    "カルヴィーノ", "ウンベルト・エーコ", "ミラン・クンデラ",
    "ブロンテ", "ジェイン・オースティン",
]

# ── ユーティリティ ──────────────────────────────────────────

def is_foreign_author(name):
    if not name:
        return False
    clean = re.sub(r'[\s,，.．()（）「」\[\]【】\d０-９:：/／;；]+', '', name)
    if not clean:
        return False
    if '・' in name or '＝' in name:
        return True
    katakana = sum(1 for c in clean if '\u30A0' <= c <= '\u30FF' or c in 'ー')
    return len(clean) > 0 and katakana / len(clean) >= 0.7


def clean_title(raw):
    if not raw:
        return ''
    t = raw.strip()
    t = re.sub(r'\s*[\(（【\[]\s*(上|中|下|[0-9０-９]+)\s*[\)）】\]]', '', t)
    t = re.sub(r'\s+第?[0-9０-９]+[巻冊編]$', '', t)
    t = re.sub(r'\s*:\s*(上巻|中巻|下巻|第[0-9０-９]+巻).*$', '', t)
    t = re.sub(r'\s+(上|下|上巻|下巻)$', '', t)
    return t.strip()


# ── SRU API（二重エスケープ対応） ───────────────────────────

def sru_search(cql_query, start_record=1, max_records=100):
    encoded = quote(cql_query)
    url = (f"{SRU_BASE}?operation=searchRetrieve"
           f"&maximumRecords={max_records}"
           f"&startRecord={start_record}"
           f"&query={encoded}")
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    })
    with urllib.request.urlopen(req, timeout=60) as res:
        return res.read()


def parse_sru_response(xml_bytes):
    entries = []
    total = 0

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return entries, total

    # numberOfRecords
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'numberOfRecords' and elem.text:
            try:
                total = int(elem.text)
            except ValueError:
                pass
            break

    # recordData は中身がHTMLエスケープされたXML文字列
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag != 'recordData':
            continue

        # recordData のテキスト全体を取得してアンエスケープ
        raw_text = ''.join(elem.itertext())
        inner_xml = unescape(raw_text)

        title = ''
        authors = []
        description = ''
        publisher = ''

        # dc:title, dc:creator 等を正規表現で抽出（確実な方法）
        for m in re.finditer(r'<dc:title>(.*?)</dc:title>', inner_xml):
            if not title:
                title = m.group(1).strip()

        for m in re.finditer(r'<dc:creator>(.*?)</dc:creator>', inner_xml):
            authors.append(m.group(1).strip())

        for m in re.finditer(r'<dc:description>(.*?)</dc:description>', inner_xml):
            if not description:
                description = m.group(1).strip()

        for m in re.finditer(r'<dc:publisher>(.*?)</dc:publisher>', inner_xml):
            if not publisher:
                publisher = m.group(1).strip()

        if title:
            entries.append({
                'title': title,
                'authors': authors,
                'description': description,
                'publisher': publisher,
            })

    return entries, total


# ── メイン処理 ──────────────────────────────────────────────

def search_by_authors(conn, author_list, foreign_score, plain_score, category):
    cursor = conn.cursor()
    grand_total = 0
    all_titles = []

    for author in author_list:
        cql = f'creator="{author}"'
        start = 1
        author_added = 0
        max_per_author = 200

        while start <= max_per_author:
            try:
                xml_bytes = sru_search(cql, start_record=start, max_records=100)
            except Exception as e:
                print(f"    APIエラー ({author}): {e}")
                break

            entries, total = parse_sru_response(xml_bytes)

            if not entries:
                break

            for entry in entries:
                # 著者フィールドに外国人名が含まれるか確認
                has_foreign = any(is_foreign_author(a) for a in entry['authors'])
                if not has_foreign:
                    # 検索対象著者名自体で判定
                    has_foreign = is_foreign_author(author)
                if not has_foreign:
                    continue

                title = clean_title(entry['title'])
                if not title or len(title) < 2:
                    continue

                author_str = ', '.join(entry['authors']) if entry['authors'] else author

                cursor.execute("SELECT 1 FROM books WHERE title = ?", (title,))
                if cursor.fetchone():
                    continue

                book_id = f"NDL_{category}_{abs(hash(title + author_str)) % 10000000}"

                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO books
                        (id, title, author, description, era,
                         origin_domestic, popularity, style_score, category)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (book_id, title, author_str, entry['description'],
                          2000, foreign_score, plain_score, plain_score, category))
                    if cursor.rowcount > 0:
                        author_added += 1
                        all_titles.append(title)
                except sqlite3.Error:
                    pass

            conn.commit()

            cap = min(total, max_per_author) if total > 0 else 0
            start += len(entries)
            if start > cap or not entries:
                break

            time.sleep(2)

        if author_added > 0:
            print(f"    {author}: +{author_added} 件")
        grand_total += author_added
        time.sleep(2)

    return grand_total, all_titles


def main():
    conn = sqlite3.connect(DB_PATH)

    print("=" * 50)
    print("第一象限（海外・平易）抽出開始")
    print(f"  対象著者: {len(Q1_AUTHORS)} 名")
    print("=" * 50)
    q1_count, q1_titles = search_by_authors(
        conn, Q1_AUTHORS, 1.0, 0.8, 'NDL_Q1')
    print(f"\n  → Q1合計: {q1_count} 件\n")

    print("=" * 50)
    print("第四象限（海外・硬質）抽出開始")
    print(f"  対象著者: {len(Q4_AUTHORS)} 名")
    print("=" * 50)
    q4_count, q4_titles = search_by_authors(
        conn, Q4_AUTHORS, 1.0, 0.1, 'NDL_Q4')
    print(f"\n  → Q4合計: {q4_count} 件\n")

    conn.close()

    result_path = os.path.join(os.path.dirname(DB_PATH),
                               'foreign_quadrants_result.txt')
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(f"第一象限（海外・平易）新規追加: {q1_count} 件\n")
        f.write(f"第四象限（海外・硬質）新規追加: {q4_count} 件\n\n")
        f.write("第一象限サンプル（5件）:\n")
        if q1_titles:
            for t in random.sample(q1_titles, min(5, len(q1_titles))):
                f.write(f"  - {t}\n")
        f.write("\n第四象限サンプル（5件）:\n")
        if q4_titles:
            for t in random.sample(q4_titles, min(5, len(q4_titles))):
                f.write(f"  - {t}\n")

    print(f"結果: {result_path}")


if __name__ == "__main__":
    main()
