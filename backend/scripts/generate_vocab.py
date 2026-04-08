#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
特異語彙辞書の自動生成スクリプト
コーパスA（青空文庫・純文学20作家）とコーパスB（小説家になろう・現代Web小説）を比較し、
Dunning's 対数尤度比(G²)により純文学特有の語彙を抽出して literary_vocab.json に保存する。
"""

import sys
import os
import re
import json
import time
import math
import requests
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from janome.tokenizer import Tokenizer

# ============================================================
# 設定: 20名の作家と代表作品 (XHTML直接URL)
# 過学習防止のため異なる20名の作家から各1作品ずつ取得
# ============================================================
WORKS = [
    {"author": "夏目漱石",   "title": "こころ",       "url": "https://www.aozora.gr.jp/cards/000148/files/773_14560.html"},
    {"author": "芥川龍之介", "title": "藪の中",       "url": "https://www.aozora.gr.jp/cards/000879/files/179_15255.html"},
    {"author": "森鷗外",     "title": "雁",           "url": "https://www.aozora.gr.jp/cards/000129/files/45224_19626.html"},
    {"author": "太宰治",     "title": "人間失格",     "url": "https://www.aozora.gr.jp/cards/000035/files/301_14912.html"},
    {"author": "梶井基次郎", "title": "檸檬",         "url": "https://www.aozora.gr.jp/cards/000074/files/424_19826.html"},
    {"author": "谷崎潤一郎", "title": "春琴抄",       "url": "https://www.aozora.gr.jp/cards/001383/files/56642_58498.html"},
    {"author": "宮沢賢治",   "title": "銀河鉄道の夜", "url": "https://www.aozora.gr.jp/cards/000081/files/456_15050.html"},
    {"author": "中島敦",     "title": "山月記",       "url": "https://www.aozora.gr.jp/cards/000119/files/624_14544.html"},
    {"author": "島崎藤村",   "title": "夜明け前",     "url": "https://www.aozora.gr.jp/cards/000158/files/1506_14669.html"},
    {"author": "志賀直哉",   "title": "暗夜行路",     "url": "https://www.aozora.gr.jp/cards/000871/files/4346_14204.html"},
    {"author": "泉鏡花",     "title": "高野聖",       "url": "https://www.aozora.gr.jp/cards/000050/files/329_15083.html"},
    {"author": "幸田露伴",   "title": "五重塔",       "url": "https://www.aozora.gr.jp/cards/000051/files/3017_6877.html"},
    {"author": "樋口一葉",   "title": "たけくらべ",   "url": "https://www.aozora.gr.jp/cards/000064/files/388_15702.html"},
    {"author": "堀辰雄",     "title": "風立ちぬ",     "url": "https://www.aozora.gr.jp/cards/000025/files/1070_14942.html"},
    {"author": "有島武郎",   "title": "生れ出づる悩み","url": "https://www.aozora.gr.jp/cards/000025/files/1137_20480.html"},
    {"author": "国木田独歩", "title": "武蔵野",       "url": "https://www.aozora.gr.jp/cards/000038/files/329_15886.html"},
    {"author": "二葉亭四迷", "title": "浮雲",         "url": "https://www.aozora.gr.jp/cards/000006/files/1869_22434.html"},
    {"author": "坂口安吾",   "title": "堕落論",       "url": "https://www.aozora.gr.jp/cards/001095/files/42620_21407.html"},
    {"author": "小林多喜二", "title": "蟹工船",       "url": "https://www.aozora.gr.jp/cards/000156/files/1465_16805.html"},
    {"author": "永井荷風",   "title": "すみだ川",     "url": "https://www.aozora.gr.jp/cards/001341/files/49659_67919.html"},
]

NAROU_API = "https://api.syosetu.com/novelapi/api/"
OUTPUT_JSON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'literary_vocab.json'))
TOP_N_VOCAB = 200

# 評価対象の品詞 (一般名詞, サ変接続名詞, 動詞自立, 形容詞自立)
VALID_POS = {('名詞', '一般'), ('名詞', 'サ変接続'), ('動詞', '自立'), ('形容詞', '自立')}

# ============================================================
# 青空文庫テキスト取得
# ============================================================

def clean_aozora_html(html_text):
    """青空文庫XHTMLからプレーンテキストを抽出・クレンジング"""
    m = re.search(r'<div class="main_text">(.*?)</div>\s*<div class="bibliographical_information">', html_text, re.DOTALL)
    if not m:
        m = re.search(r'<div class="main_text">(.*?)</div>', html_text, re.DOTALL)
    if m:
        text = m.group(1)
    else:
        body = re.search(r'<body[^>]*>(.*?)</body>', html_text, re.DOTALL)
        text = body.group(1) if body else html_text
    text = re.sub(r'<rp>[^<]*</rp>', '', text)
    text = re.sub(r'<rt>[^<]*</rt>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'《[^》]*》', '', text)
    text = re.sub(r'［＃[^］]*］', '', text)
    text = re.sub(r'｜', '', text)
    text = re.sub(r'[\s\u3000]+', ' ', text).strip()
    return text


def fetch_aozora_corpus():
    """青空文庫から20作家の代表作品テキストを直接取得"""
    print("=" * 60)
    print("コーパスA: 青空文庫（純文学）テキスト取得")
    print("=" * 60)

    all_text = []
    ok = 0

    for work in WORKS:
        author = work["author"]
        title = work["title"]
        url = work["url"]
        print(f"\n  [{author}] 『{title}』 取得中...")
        time.sleep(1)

        try:
            r = requests.get(url, timeout=15)
            r.encoding = 'shift_jis'
            text = clean_aozora_html(r.text)

            if len(text) > 500:
                print(f"    -> 成功: {len(text):,} 文字")
                all_text.append(text)
                ok += 1
            else:
                print(f"    -> テキストが短すぎます ({len(text)} 文字)。スキップ。")
        except Exception as e:
            print(f"    -> エラー: {e}")

    corpus = ' '.join(all_text)
    print(f"\nコーパスA完了: {ok}/{len(WORKS)} 作品, 総文字数: {len(corpus):,}")
    return corpus


# ============================================================
# なろうAPI テキスト取得
# ============================================================

def fetch_narou_corpus(target_chars):
    """小説家になろうAPIからあらすじを取得"""
    print("\n" + "=" * 60)
    print("コーパスB: 小説家になろう（現代Web小説）あらすじ取得")
    print("=" * 60)

    stories = []
    total_chars = 0
    genres = [1, 2]  # 1=恋愛, 2=ファンタジー

    for genre in genres:
        offset = 1
        while total_chars < target_chars:
            params = {
                "out": "json", "of": "t-s", "lim": 500,
                "st": offset, "biggenre": genre, "order": "hyoka",
            }
            try:
                resp = requests.get(NAROU_API, params=params, timeout=10)
                data = resp.json()
                if not data or len(data) <= 1:
                    break
                for item in data[1:]:
                    story = item.get("story", "")
                    # HTMLタグ除去
                    story = re.sub(r'<[^>]+>', '', story)
                    if story and len(story) > 50:
                        stories.append(story)
                        total_chars += len(story)

                print(f"  ジャンル{genre}: {len(stories)} 件, {total_chars:,} 文字")
                offset += 500
                time.sleep(1)
                if total_chars >= target_chars:
                    break
            except Exception as e:
                print(f"  なろうAPIエラー: {e}")
                time.sleep(3)
                break

    corpus = ' '.join(stories)
    print(f"\nコーパスB完了: {len(stories)} 件, 総文字数: {len(corpus):,}")
    return corpus


# ============================================================
# 形態素解析
# ============================================================

def tokenize_and_count(text, tokenizer):
    """形態素解析 → フィルタリング → 基本形でカウント"""
    counter = Counter()
    total = 0
    chunk_size = 50000
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        for token in tokenizer.tokenize(chunk):
            pos = token.part_of_speech.split(',')
            pair = (pos[0], pos[1]) if len(pos) > 1 else (pos[0], '*')
            if pair in VALID_POS:
                base = token.base_form if token.base_form != '*' else token.surface
                if len(base) >= 2:
                    counter[base] += 1
                    total += 1
    return counter, total


# ============================================================
# Dunning's 対数尤度比 (G²)
# ============================================================

def log_likelihood(a, b, c, d):
    """G²を算出。a,b=単語頻度, c,d=コーパス総トークン数"""
    N = c + d
    if N == 0:
        return 0.0, False
    E_a = c * (a + b) / N
    E_b = d * (a + b) / N
    g2 = 0.0
    if a > 0 and E_a > 0:
        g2 += a * math.log(a / E_a)
    if b > 0 and E_b > 0:
        g2 += b * math.log(b / E_b)
    g2 *= 2
    rate_a = a / c if c > 0 else 0
    rate_b = b / d if d > 0 else 0
    return g2, rate_a > rate_b


def extract_literary_vocab(ca, ta, cb, tb, top_n=200):
    """コーパスAに特異的な語彙をG²値で抽出"""
    scored = []
    for word in set(ca.keys()) | set(cb.keys()):
        a, b = ca.get(word, 0), cb.get(word, 0)
        if a < 3:
            continue
        g2, is_a = log_likelihood(a, b, ta, tb)
        if is_a and g2 > 0:
            scored.append((word, g2, a, b))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_n]

    vocab = {}
    if top:
        max_g2 = top[0][1]
        for w, g2, a, b in top:
            vocab[w] = round(g2 / max_g2, 4)

    return vocab, top


# ============================================================
# メイン
# ============================================================

def main():
    print("特異語彙辞書生成スクリプト 開始\n")
    tokenizer = Tokenizer()

    corpus_a = fetch_aozora_corpus()
    if not corpus_a:
        print("エラー: コーパスAの取得に失敗"); return

    corpus_b = fetch_narou_corpus(target_chars=len(corpus_a))
    if not corpus_b:
        print("エラー: コーパスBの取得に失敗"); return

    print("\n形態素解析中...")
    print("  コーパスA（純文学）...")
    ca, ta = tokenize_and_count(corpus_a, tokenizer)
    print(f"    {ta:,} トークン, {len(ca):,} ユニーク語")

    print("  コーパスB（Web小説）...")
    cb, tb = tokenize_and_count(corpus_b, tokenizer)
    print(f"    {tb:,} トークン, {len(cb):,} ユニーク語")

    print("\nG²による特異語彙抽出...")
    vocab, ranked = extract_literary_vocab(ca, ta, cb, tb, TOP_N_VOCAB)

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(vocab, f, ensure_ascii=False, indent=2)

    print(f"\n辞書保存: {OUTPUT_JSON} ({len(vocab)} 語)")
    print(f"\n{'順位':>4} {'語':>10} {'G2':>10} {'A出現':>6} {'B出現':>6} {'スコア':>6}")
    print("-" * 55)
    for i, (w, g2, a, b) in enumerate(ranked[:20], 1):
        print(f"{i:4d} {w:>10} {g2:10.1f} {a:6d} {b:6d} {vocab[w]:6.4f}")

    print("\n完了!")

if __name__ == "__main__":
    main()
