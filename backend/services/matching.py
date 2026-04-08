import numpy as np
from sqlalchemy.orm import Session
from models import Book, SearchQuery


def cosine_similarity(v1, v2):
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return float(dot_product / (norm_v1 * norm_v2))


def find_best_match(db: Session, query: SearchQuery) -> Book:
    """
    3次元ベクトル空間マッチング（年代、認知度、文体）。

    Pre-filter（絶対条件）:
      1. 属性（Origin）: origin_domestic の完全一致で候補を絞り込む。
      2. テーマ（Keywords）: title/description にキーワードを含む書籍のみに絞り込む。
    いずれも該当0件なら None を返す（API側で404）。

    距離計算:
      絞り込み後の候補に対して、残り3軸（年代・認知度・文体）で
      コサイン類似度を計算し、最も近い1冊を返す。
    """
    books = db.query(Book).all()
    if not books:
        return None

    # === Pre-filter 段階 ===

    # 1. 属性（Origin）のハードフィルター — 絶対条件
    books = [b for b in books if b.origin_domestic == query.origin_domestic]
    if not books:
        return None

    # 2. テーマ（Keywords）のハードフィルター — 絶対条件
    keywords = []
    if query.keywords:
        keywords = [kw.strip() for kw in query.keywords.replace("、", ",").split(",") if kw.strip()]

    if keywords:
        filtered = []
        for book in books:
            text = (book.title or "") + " " + (book.description or "")
            if any(kw in text for kw in keywords):
                filtered.append(book)
        if not filtered:
            return None
        books = filtered

    # === 3次元ベクトル空間マッチング（年代・認知度・文体） ===
    MIN_ERA = 1800
    MAX_ERA = 2050

    def normalize_era(era):
        e = max(MIN_ERA, min(MAX_ERA, era))
        return (e - MIN_ERA) / (MAX_ERA - MIN_ERA)

    q_era_center = (query.era_min + query.era_max) / 2.0
    q_era_norm = normalize_era(q_era_center)

    q_vec = np.array([
        q_era_norm,
        query.popularity,
        query.style_score
    ])

    best_book = None
    best_score = -1.0

    for book in books:
        b_era_norm = normalize_era(book.era)
        b_vec = np.array([
            b_era_norm,
            book.popularity,
            book.style_score
        ])

        sim = cosine_similarity(q_vec, b_vec)

        # 年代がレンジ内ならボーナス
        if query.era_min <= book.era <= query.era_max:
            sim += 0.05

        if sim > best_score:
            best_score = sim
            best_book = book

    return best_book
