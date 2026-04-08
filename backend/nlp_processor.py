import re
from typing import Dict, List, Tuple, Optional

class QueryVectorizer:
    """
    自然言語クエリを4次元ベクトル(ERA, ORIGIN, STYLE, RENOWN)に変換する。
    カント的自律に基づき、無駄を排した最短のヒューリスティック変換を行う。
    """
    
    # カテゴリ・キーワード
    KEYWORDS = {
        "era": {
            "古典": 0.1, "明治": 0.1, "19世紀": 0.1, "大正": 0.2, "近代": 0.3,
            "昭和": 0.5, "戦後": 0.5, "20世紀": 0.6,
            "現代": 0.9, "最近": 0.9, "新刊": 1.0, "21世紀": 1.0
        },
        "origin": {
            "海外": 1.0, "翻訳": 1.0, "洋書": 1.0, "外国": 1.0, "欧米": 1.0,
            "国内": 0.0, "日本": 0.0, "和物": 0.1, "邦訳": 0.5 # 邦訳は中間的
        },
        "style": {
            "哲学": 1.0, "思想": 1.0, "難しい": 1.0, "硬い": 1.0, "学術": 1.0, "論": 0.8,
            "読みやすい": 0.0, "ほのぼの": 0.0, "ライト": 0.0, "簡単": 0.0, "易しい": 0.2
        },
        "renown": {
            "有名": 1.0, "ベストセラー": 1.0, "定番": 1.0, "代表作": 0.9,
            "隠れた": 0.0, "マイナー": 0.0, "知る人ぞ知る": 0.0, "新進気鋭": 0.3
        },
        "category": {
            "漫画": "manga", "マンガ": "manga", "コミック": "manga",
            "活字": "book", "小説": "book", "書籍": "book", "文芸": "book"
        }
    }

    @classmethod
    def vectorize(cls, query: str) -> Tuple[List[float], Optional[str], Optional[str]]:
        """
        クエリから[ERA, ORIGIN, STYLE, RENOWN]ベクトル、カテゴリ、キーワードを抽出。
        """
        # デフォルトは中庸 (0.5を中心に、歴史は現代寄り0.8)
        vector = [0.8, 0.0, 0.5, 0.5]
        category = None
        keyword = None

        query = query.lower()

        # ERAの検知
        for k, v in cls.KEYWORDS["era"].items():
            if k in query:
                vector[0] = v
                break
        
        # ORIGINの検知
        for k, v in cls.KEYWORDS["origin"].items():
            if k in query:
                vector[1] = v
                break
            
        # STYLEの検知
        for k, v in cls.KEYWORDS["style"].items():
            if k in query:
                vector[2] = v
                break

        # RENOWNの検知
        for k, v in cls.KEYWORDS["renown"].items():
            if k in query:
                vector[3] = v
                break

        # カテゴリの強制指定があれば抽出
        for k, v in cls.KEYWORDS["category"].items():
            if k in query:
                category = v
                break

        # キーワード抽出 (「○○について」「○○の本」といった表現から)
        kw_match = re.search(r'([^\s、。]+)(?:について|の(?:本|漫画|マンガ|書籍))', query)
        if kw_match:
            keyword = kw_match.group(1)
        elif len(query.split()) == 1 and not any(k in query for sub in cls.KEYWORDS.values() for k in sub):
            # 1単語でどのキーワードにも属さないなら検索語とする
            keyword = query

        return vector, category, keyword

if __name__ == "__main__":
    # 単体テスト
    test_queries = [
        "哲学的なSF漫画、少し古め",
        "心が温まる、知名度のある活字本",
        "古典的な海外の小説",
        "SF"
    ]
    for q in test_queries:
        v, c, k = QueryVectorizer.vectorize(q)
        print(f"Q: {q} -> V:{v}, C:{c}, K:{k}")
