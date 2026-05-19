"""
Lemma NLP Processor — 自然言語クエリ → 4Dベクトル変換
カント的自律に基づき、無駄を排した最短のヒューリスティック変換を行う。
"""

import re
from typing import Tuple, Optional

# --- 定数: デフォルトベクトル ---
DEFAULT_ERA = 0.8  # 現代寄り
DEFAULT_ORIGIN = 0.0  # 国内
DEFAULT_STYLE = 0.5  # 中庸
DEFAULT_RENOWN = 0.5  # 中庸

# --- キーワード → スカラー値 マッピング ---
_ERA_KEYWORDS = {
    "古典": 0.1,
    "明治": 0.1,
    "19世紀": 0.1,
    "大正": 0.2,
    "近代": 0.3,
    "昭和": 0.5,
    "戦後": 0.5,
    "20世紀": 0.6,
    "現代": 0.9,
    "最近": 0.9,
    "新刊": 1.0,
    "21世紀": 1.0,
}

_ORIGIN_KEYWORDS = {
    "海外": 1.0,
    "翻訳": 1.0,
    "洋書": 1.0,
    "外国": 1.0,
    "欧米": 1.0,
    "国内": 0.0,
    "日本": 0.0,
    "和物": 0.1,
    "邦訳": 0.5,
}

_STYLE_KEYWORDS = {
    "哲学": 1.0,
    "思想": 1.0,
    "難しい": 1.0,
    "硬い": 1.0,
    "学術": 1.0,
    "論": 0.8,
    "読みやすい": 0.0,
    "ほのぼの": 0.0,
    "ライト": 0.0,
    "簡単": 0.0,
    "易しい": 0.2,
}

_RENOWN_KEYWORDS = {
    "有名": 1.0,
    "ベストセラー": 1.0,
    "定番": 1.0,
    "代表作": 0.9,
    "隠れた": 0.0,
    "マイナー": 0.0,
    "知る人ぞ知る": 0.0,
    "新進気鋭": 0.3,
}

_CATEGORY_KEYWORDS = {
    "漫画": "manga",
    "マンガ": "manga",
    "コミック": "manga",
    "活字": "book",
    "小説": "book",
    "書籍": "book",
    "文芸": "book",
}

# キーワード抽出用の正規表現パターン
_KEYWORD_PATTERN = re.compile(r"([^\s、。]+)(?:について|の(?:本|漫画|マンガ|書籍))")

# 全キーワード集合（単語判定用）
_ALL_KEYWORDS = set()
for mapping in [
    _ERA_KEYWORDS,
    _ORIGIN_KEYWORDS,
    _STYLE_KEYWORDS,
    _RENOWN_KEYWORDS,
    _CATEGORY_KEYWORDS,
]:
    _ALL_KEYWORDS.update(mapping.keys())


class QueryVectorizer:
    """自然言語クエリを4次元ベクトル (ERA, ORIGIN, STYLE, RENOWN) に変換する。"""

    @staticmethod
    def _detect_value(query: str, keyword_map: dict[str, float]) -> float | None:
        """クエリ内のキーワードを検知し、対応するスカラー値を返す。"""
        for keyword, value in keyword_map.items():
            if keyword in query:
                return value
        return None

    @classmethod
    def vectorize(cls, query: str) -> Tuple[list[float], Optional[str], Optional[str]]:
        """
        クエリから [ERA, ORIGIN, STYLE, RENOWN] ベクトル、カテゴリ、キーワードを抽出。

        Returns:
            (vector, category, keyword) のタプル
        """
        vector = [DEFAULT_ERA, DEFAULT_ORIGIN, DEFAULT_STYLE, DEFAULT_RENOWN]
        category: str | None = None
        keyword: str | None = None

        query_lower = query.lower()

        # 各軸のキーワード検知
        vector[0] = cls._detect_value(query_lower, _ERA_KEYWORDS) or DEFAULT_ERA
        vector[1] = cls._detect_value(query_lower, _ORIGIN_KEYWORDS) or DEFAULT_ORIGIN
        vector[2] = cls._detect_value(query_lower, _STYLE_KEYWORDS) or DEFAULT_STYLE
        vector[3] = cls._detect_value(query_lower, _RENOWN_KEYWORDS) or DEFAULT_RENOWN

        # カテゴリの検知
        for kw, cat in _CATEGORY_KEYWORDS.items():
            if kw in query_lower:
                category = cat
                break

        # キーワード抽出 (「○○について」「○○の本」)
        kw_match = _KEYWORD_PATTERN.search(query_lower)
        if kw_match:
            keyword = kw_match.group(1)
        elif len(query_lower.split()) == 1 and not any(
            k in query_lower for k in _ALL_KEYWORDS
        ):
            # 1単語でどのキーワードにも属さないなら検索語とする
            keyword = query_lower

        return vector, category, keyword
