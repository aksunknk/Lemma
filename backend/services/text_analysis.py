"""
形態素解析(janome)＋特異語彙辞書を用いた文体スコア評価ロジック。
コーパス比較で生成された literary_vocab.json を参照し、
あらすじ内の純文学特異語彙の出現密度から Style スコア(0.0〜1.0)を算出する。
"""
import os
import json
from janome.tokenizer import Tokenizer

tokenizer = Tokenizer()

# --- 特異語彙辞書のロード ---
_VOCAB_PATH = os.path.join(os.path.dirname(__file__), '..', 'literary_vocab.json')
_literary_vocab = {}

if os.path.exists(_VOCAB_PATH):
    with open(_VOCAB_PATH, 'r', encoding='utf-8') as f:
        _literary_vocab = json.load(f)
    print(f"[text_analysis] 特異語彙辞書ロード完了: {len(_literary_vocab)} 語")
else:
    print(f"[text_analysis] 警告: {_VOCAB_PATH} が見つかりません。フォールバックモードで動作します。")

# 評価対象の品詞 (generate_vocab.py と同一基準)
VALID_POS = {('名詞', '一般'), ('名詞', 'サ変接続'), ('動詞', '自立'), ('形容詞', '自立')}


def calculate_style_score(text: str) -> float:
    """
    文体スコア(Style)を算出する。

    特異語彙辞書が存在する場合:
      あらすじを形態素解析し、辞書に含まれる純文学特異語彙の
      「重み付き出現密度」をベースに 0.0〜1.0 のスコアを返す。
      - 0.0 に近い = カジュアル/現代的な文体
      - 1.0 に近い = 堅い/文学的な文体

    辞書が未生成の場合:
      従来の漢語比率ベースのフォールバックを使用。
    """
    if not text:
        return 0.5

    # --- 辞書ベーススコアリング ---
    if _literary_vocab:
        tokens = list(tokenizer.tokenize(text))
        if not tokens:
            return 0.5

        total_valid = 0
        weighted_hits = 0.0

        for token in tokens:
            pos = token.part_of_speech.split(',')
            pair = (pos[0], pos[1]) if len(pos) > 1 else (pos[0], '*')

            if pair in VALID_POS:
                base = token.base_form if token.base_form != '*' else token.surface
                total_valid += 1

                if base in _literary_vocab:
                    weighted_hits += _literary_vocab[base]

        if total_valid == 0:
            return 0.5

        # 密度を算出し、0.0〜1.0にスケーリング
        # 典型的な純文学テキストで density ≈ 0.15〜0.25 程度
        # 典型的なWeb小説あらすじで density ≈ 0.02〜0.05 程度
        density = weighted_hits / total_valid
        # 線形スケール: density 0.0 → score 0.0, density 0.15 → score 1.0
        score = density / 0.15
        return max(0.0, min(1.0, score))

    # --- フォールバック: 漢語比率ベース (辞書なし時) ---
    tokens = list(tokenizer.tokenize(text))
    if not tokens:
        return 0.5

    noun_count = 0
    complex_noun_count = 0

    for token in tokens:
        pos = token.part_of_speech.split(',')
        if pos[0] == '名詞':
            noun_count += 1
            surface = token.surface
            if len(surface) >= 2 and all('\u4e00' <= c <= '\u9faf' for c in surface):
                complex_noun_count += 1

    if noun_count == 0:
        return 0.5

    ratio = complex_noun_count / noun_count
    score = ratio / 0.4
    return max(0.0, min(1.0, score))
