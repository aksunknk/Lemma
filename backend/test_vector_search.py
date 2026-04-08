import sqlite3
import math

DB_PATH = "lemma_master.db"

def calc_distance(e1, o1, s1, r1, e2, o2, s2, r2):
    """4次元ユークリッド距離の計算"""
    return math.sqrt(
        (e1 - e2)**2 +
        (o1 - o2)**2 +
        (s1 - s2)**2 +
        (r1 - r2)**2
    )

def search_vector(cursor, target, threshold=0.3):
    t_e, t_o, t_s, t_r = target
    
    # 距離計算関数を利用して検索 (インデックスが効く範囲で高速化)
    # era, origin, style, renown の範囲を絞ることで更に高速化可能だが、
    # 100万件程度なら全件走査でも数秒以内。
    cursor.execute("""
        SELECT title, author, publisher, era, origin, style, renown, 
               distance(era, origin, style, renown, ?, ?, ?, ?) as d
        FROM books
        ORDER BY d ASC
        LIMIT 3
    """, (t_e, t_o, t_s, t_r))
    
    results = cursor.fetchall()
    
    if not results or results[0][-1] > threshold:
        return None
    return results

def run_tests():
    conn = sqlite3.connect(DB_PATH)
    # カスタム関数の登録
    conn.create_function("distance", 8, calc_distance)
    cursor = conn.cursor()

    test_cases = [
        {"label": "現代/国内/平易/有名 (メジャーエンタメ)", "v": (0.9, 0.0, 0.2, 0.9), "t": 0.5},
        {"label": "古典/海外/硬質/有名 (海外古典・哲学)", "v": (0.1, 1.0, 0.9, 0.8), "t": 0.5},
        {"label": "現代/国内/硬質/ニッチ (専門書・学術書)", "v": (0.8, 0.0, 0.8, 0.1), "t": 0.5},
        {"label": "中世/海外/平易/ニッチ (マイナーエッセイ)", "v": (0.4, 1.0, 0.3, 0.2), "t": 0.5},
        {"label": "ニュートラル (空間中心点)", "v": (0.5, 0.5, 0.5, 0.5), "t": 0.5},
        {"label": "極めて古い国内書 (近世以前)", "v": (0.05, 0.0, 0.7, 0.5), "t": 0.5},
        {"label": "最新の国内ライト文芸", "v": (0.98, 0.0, 0.1, 0.7), "t": 0.5},
        {"label": "海外の超有名現代小説", "v": (0.9, 1.0, 0.4, 0.9), "t": 0.5},
        {"label": "国内の超硬質現代思想", "v": (0.9, 0.0, 1.0, 0.4), "t": 0.5},
        {"label": "歴史小説 (戦国・幕末)", "v": (0.7, 0.0, 0.6, 0.8), "t": 0.5},
        {"label": "海外の古い詩集・文学", "v": (0.2, 1.0, 0.8, 0.3), "t": 0.5},
        {"label": "ビジネス・自己啓発", "v": (0.95, 0.3, 0.5, 0.8), "t": 0.5},
        {"label": "宗教・精神世界", "v": (0.4, 0.2, 0.6, 0.4), "t": 0.5},
        {"label": "国内のマイナー専門書", "v": (0.8, 0.0, 0.9, 0.05), "t": 0.5},
        {"label": "海外のサイエンス・テクノロジー", "v": (0.9, 1.0, 0.8, 0.6), "t": 0.5},
        
        # 404をあえて発生させるケース
        {"label": "存在しない極限値 (404期待)", "v": (0.0, 0.5, 0.0, 0.0), "t": 0.15},
        {"label": "超厳格な閾値 (404期待)", "v": (0.5, 0.5, 0.5, 0.5), "t": 0.01},
        {"label": "未来予測? (1.0オーバー)", "v": (1.1, -0.1, 1.1, 1.1), "t": 0.3},
        {"label": "超有名/超古い/超平易/国内 (極端な偏り)", "v": (0.0, 0.0, 0.0, 1.0), "t": 0.3},
        {"label": "完全に空疎な空間 (404期待)", "v": (0.3, 0.7, 0.1, 0.1), "t": 0.1},
    ]

    print(f"\n{'='*80}")
    print(f"--- lemma Master Vector Search Validation (Records: 1.1M) ---")
    print(f"{'='*80}\n")

    for i, case in enumerate(test_cases, 1):
        print(f"CASE {i:02}: {case['label']}")
        print(f"TARGET V: {case['v']} | Threshold: {case['t']}")
        
        results = search_vector(cursor, case['v'], threshold=case['t'])
        
        if results is None:
            print(f"\033[91m[誠実な沈黙 (404)] 許容範囲内に合致する書籍が存在しません。\033[0m")
        else:
            for rank, r in enumerate(results, 1):
                title, author, pub, e, o, s, ren, dist = r
                print(f"  {rank}. {title} ({author}) / {pub}")
                print(f"     Dist: {dist:.4f} | V: ({e:.2f}, {o:.2f}, {s:.2f}, {ren:.2f})")
        print("-" * 40)

    conn.close()

if __name__ == "__main__":
    run_tests()
