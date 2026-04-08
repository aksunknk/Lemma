# -*- coding: utf-8 -*-
"""
seed_aozora.py — 青空文庫のアクセスランキングから作品を取得し、
テキストを抽出・クレンジング・スコアリングしてDBへ投入するスクリプト。

使い方:
  python seed_aozora.py              # 上位500件を取得
  python seed_aozora.py --limit 5    # テスト用: 上位5件のみ
  python seed_aozora.py --resume     # 既存データをスキップして続行
"""
import os
import sys
import re
import time
import sqlite3
import hashlib
import argparse
import urllib.request
from html.parser import HTMLParser

# --- text_analysis へのパスを通す ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from services.text_analysis import calculate_style_score

# --- 設定 ---
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'books.db')
RANKING_URL = "https://www.aozora.gr.jp/access_ranking/2022_xhtml.html"
BASE_URL = "https://www.aozora.gr.jp"
REQUEST_DELAY = 1.0
MAX_DESC_CHARS = 1000


# ========================================================================
#  ユーティリティ
# ========================================================================

def fetch_url(url: str) -> str:
    """URLからHTMLを取得。エンコーディング自動判別。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": "SingleBookEngine/1.0 (Educational Project)"
    })
    with urllib.request.urlopen(req, timeout=15) as res:
        raw = res.read()
        content_type = res.headers.get("Content-Type", "")
        encoding = "utf-8"
        if "charset=" in content_type.lower():
            encoding = content_type.lower().split("charset=")[-1].strip().split(";")[0]
        for enc in [encoding, "utf-8", "shift_jis", "euc-jp"]:
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("utf-8", errors="replace")


def clean_aozora_text(text: str) -> str:
    """青空文庫テキストからルビ・注釈・制御記号を除去しプレーンテキスト化。"""
    text = re.sub(r'《[^》]*》', '', text)
    text = re.sub(r'［＃[^］]*］', '', text)
    text = text.replace('｜', '')
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ========================================================================
#  ランキングページ解析（正規表現ベース）
# ========================================================================

def get_ranking_entries(url: str, limit: int = 500) -> list:
    """
    ランキングページ（テーブル構造）から作品情報を正規表現で抽出。
    各 <tr> 内に:
      <td> 順位 </td>
      <td> <a href="カードURL">タイトル</a> </td>
      <td> <a href="著者URL">著者名</a> </td>
    の形式で並んでいる。
    """
    print(f"[INFO] ランキングページ取得中: {url}")
    html = fetch_url(url)

    # <tr> ... </tr> のブロックを抽出
    tr_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
    # <a> タグからhrefとテキストを抽出
    a_pattern = re.compile(r'<a\s+[^>]*href=["\']?([^"\'>\s]+)["\']?[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE)

    entries = []
    for tr_match in tr_pattern.finditer(html):
        tr_content = tr_match.group(1)
        links = a_pattern.findall(tr_content)

        # カードURLと著者URLのペアを探す
        card_link = None
        author_name = None
        title = None

        for href, text in links:
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            if "/cards/" in href and "card" in href:
                card_link = href
                title = clean_text
            elif "/index_pages/person" in href:
                author_name = clean_text

        if card_link and title and author_name:
            if card_link.startswith("/"):
                card_link = BASE_URL + card_link
            elif not card_link.startswith("http"):
                card_link = BASE_URL + "/" + card_link
            entries.append((title, card_link, author_name))

        if len(entries) >= limit:
            break

    print(f"[INFO] {len(entries)} 件の作品を検出")
    return entries


# ========================================================================
#  カードページ → 本文URL → テキスト抽出
# ========================================================================

def get_xhtml_url_from_card(card_url: str) -> str | None:
    """図書カードページからXHTML本文URLを取得。"""
    html = fetch_url(card_url)
    # 「いますぐXHTML版で読む」リンクを探す
    pattern = re.compile(r'<a\s+[^>]*href=["\']?([^"\'>\s]+)["\']?[^>]*>[^<]*いますぐXHTML版で読む', re.DOTALL)
    match = pattern.search(html)
    if match:
        href = match.group(1)
        if href.startswith("/"):
            return BASE_URL + href
        elif not href.startswith("http"):
            base_dir = card_url.rsplit("/", 1)[0]
            return base_dir + "/" + href
        return href

    # フォールバック: /files/ 内の .html ファイル
    fallback = re.compile(r'<a\s+[^>]*href=["\']?([^"\'>\s]*?/files/[^"\'>\s]*\.html)["\']?', re.IGNORECASE)
    match = fallback.search(html)
    if match:
        href = match.group(1)
        if href.startswith("/"):
            return BASE_URL + href
        elif not href.startswith("http"):
            base_dir = card_url.rsplit("/", 1)[0]
            return base_dir + "/" + href
        return href

    return None


class BodyTextParser(HTMLParser):
    """XHTML本文ページから <body> 内のテキストを抽出。"""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._in_body = False
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self._in_body = True
        elif tag in ("rp", "rt", "script", "style"):
            self._skip_depth += 1

    def handle_data(self, data):
        if self._in_body and self._skip_depth == 0:
            self.text_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "body":
            self._in_body = False
        elif tag in ("rp", "rt", "script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)


def extract_body_text(xhtml_url: str, max_chars: int = MAX_DESC_CHARS) -> str:
    """XHTML本文ページからテキストを抽出しクレンジング。"""
    html = fetch_url(xhtml_url)
    parser = BodyTextParser()
    parser.feed(html)
    raw_text = "".join(parser.text_parts)
    cleaned = clean_aozora_text(raw_text)
    return cleaned[:max_chars]


# ========================================================================
#  スコアリング補助
# ========================================================================

def calculate_popularity(rank: int, total: int) -> float:
    """ランキング順位から認知度スコア(0.1~1.0)を線形正規化。"""
    if total <= 1:
        return 1.0
    return max(0.1, 1.0 - (rank - 1) * 0.9 / (total - 1))


def estimate_era(title: str, author: str) -> int:
    """著者名から大まかな時代を推定（青空文庫 = 基本的に戦前〜昭和初期）。"""
    known_eras = {
        "紀 貫之": 935, "鴨 長明": 1212, "兼好法師": 1330, "吉田 兼好": 1330,
        "井原 西鶴": 1693, "近松 門左衛門": 1710, "松尾 芭蕉": 1694,
        "福沢 諭吉": 1872, "樋口 一葉": 1896,
        "夏目 漱石": 1910, "森 鴎外": 1910, "芥川 竜之介": 1925,
        "太宰 治": 1940, "宮沢 賢治": 1930, "梶井 基次郎": 1928,
        "中島 敦": 1942, "夢野 久作": 1935, "坂口 安吾": 1947,
        "江戸川 乱歩": 1930, "織田 作之助": 1946, "萩原 朔太郎": 1917,
        "高村 光太郎": 1914, "新美 南吉": 1938, "中原 中也": 1934,
        "島崎 藤村": 1906, "北原 白秋": 1909, "石川 啄木": 1910,
        "有島 武郎": 1918, "菊池 寛": 1920, "横光 利一": 1930,
        "堀 辰雄": 1937, "小林 多喜二": 1929, "宮本 百合子": 1935,
        "泉 鏡花": 1900, "田山 花袋": 1907, "国木田 独歩": 1901,
        "徳田 秋声": 1910, "正岡 子規": 1897, "岡本 綺堂": 1917,
        "三好 達治": 1934, "室生 犀星": 1919, "折口 信夫": 1929,
        "柳田 国男": 1910, "南方 熊楠": 1900, "内田 百間": 1930,
        "寺田 寅彦": 1920, "与謝野 晶子": 1901,
    }
    return known_eras.get(author, 1920)


# ========================================================================
#  メイン処理
# ========================================================================

def main():
    parser = argparse.ArgumentParser(description="青空文庫シードスクリプト")
    parser.add_argument("--limit", type=int, default=500, help="取得件数上限 (default: 500)")
    parser.add_argument("--resume", action="store_true", help="既存データをスキップ")
    args = parser.parse_args()

    db_path = os.path.abspath(DB_PATH)
    print(f"[INFO] DB: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books'")
    if not cursor.fetchone():
        print("[ERROR] 'books' テーブルが存在しません。")
        return

    existing_ids = set()
    if args.resume:
        cursor.execute("SELECT id FROM books WHERE id LIKE 'aozora-%'")
        existing_ids = {row[0] for row in cursor.fetchall()}
        print(f"[INFO] 既存の青空文庫レコード: {len(existing_ids)} 件")

    entries = get_ranking_entries(RANKING_URL, args.limit)
    total = len(entries)

    if total == 0:
        print("[ERROR] ランキングから作品を取得できませんでした。")
        return

    inserted = 0
    skipped = 0
    errors = 0

    for rank, (title, card_url, author) in enumerate(entries, 1):
        book_id = "aozora-" + hashlib.md5(card_url.encode()).hexdigest()[:12]

        if book_id in existing_ids:
            print(f"  [{rank}/{total}] SKIP (既存): {title}")
            skipped += 1
            continue

        print(f"  [{rank}/{total}] {title} / {author}")

        try:
            time.sleep(REQUEST_DELAY)
            xhtml_url = get_xhtml_url_from_card(card_url)
            if not xhtml_url:
                print(f"    ⚠ XHTML本文URLが見つかりません。スキップ。")
                errors += 1
                continue

            time.sleep(REQUEST_DELAY)
            body_text = extract_body_text(xhtml_url)
            if not body_text or len(body_text) < 50:
                print(f"    ⚠ 本文テキストが短すぎます ({len(body_text) if body_text else 0}文字)。スキップ。")
                errors += 1
                continue

            style_score = calculate_style_score(body_text)
            popularity = calculate_popularity(rank, total)
            era = estimate_era(title, author)

            cursor.execute("""
                INSERT OR REPLACE INTO books (id, title, author, description, image_url,
                                              era, origin_domestic, popularity, style_score, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                book_id, title, author, body_text, None,
                era, True, round(popularity, 4), round(style_score, 4), "aozora"
            ))
            conn.commit()
            inserted += 1
            print(f"    ✓ era={era}, pop={popularity:.3f}, style={style_score:.3f}")
            print(f"    冒頭: {body_text[:80]}...")

        except Exception as e:
            print(f"    ✗ エラー: {e}")
            errors += 1
            continue

    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM books WHERE category = 'aozora'")
    aozora_books = cursor.fetchone()[0]

    print("\n" + "=" * 60)
    print(f"完了: 挿入={inserted}, スキップ={skipped}, エラー={errors}")
    print(f"DB合計: {total_books} 冊 (うち青空文庫: {aozora_books} 冊)")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
