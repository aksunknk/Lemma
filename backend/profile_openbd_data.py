import sqlite3
import random

# 設定
DB_PATH = "openbd_supplement.db"
NOISE_KEYWORDS = ['カレンダー', '版', 'セット', 'CD', 'DVD', '特装', '公式ガイド']

def profile():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 基本統計
    cursor.execute("SELECT COUNT(*) FROM books")
    total_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM books WHERE description IS NOT NULL AND description != ''")
    desc_count = cursor.fetchone()[0]
    desc_ratio = (desc_count / total_count * 100) if total_count > 0 else 0
    
    # 2. 4次元ベクトルの分布
    stats = {}
    for col in ['era', 'origin', 'style', 'renown']:
        cursor.execute(f"SELECT AVG({col}), MIN({col}), MAX({col}) FROM books")
        avg_val, min_val, max_val = cursor.fetchone()
        stats[col] = {'avg': avg_val, 'min': min_val, 'max': max_val}
        
    # 3. 残存ノイズの検知
    noise_counts = {}
    total_noise = 0
    for keyword in NOISE_KEYWORDS:
        cursor.execute("SELECT COUNT(*) FROM books WHERE title LIKE ?", (f'%{keyword}%',))
        count = cursor.fetchone()[0]
        noise_counts[keyword] = count
        total_noise += count
        
    # 4. ランダム目視検査 (10件)
    # categories/CコードはDBに存在しないため、title, author, publisherを抽出
    cursor.execute("SELECT title, author, publisher, era, origin, style, renown FROM books ORDER BY RANDOM() LIMIT 10")
    samples = cursor.fetchall()
    
    # ターミナル出力
    print("-" * 50)
    print(f"=== [lemma] Database Profiling Report: {DB_PATH} ===")
    print("-" * 50)
    print(f"1. Basic Statistics:")
    print(f"   Total Records: {total_count:,}")
    print(f"   With Description: {desc_count:,} ({desc_ratio:.2f}%)")
    print("-" * 50)
    print(f"2. 4D Vector Distributions:")
    for col, s in stats.items():
        print(f"   [{col.upper():<6}] Avg: {s['avg']:.4f} | Min: {s['min']:.4f} | Max: {s['max']:.4f}")
    print("-" * 50)
    print(f"3. Potential Noise (Title keyword match):")
    for k, c in noise_counts.items():
        if c > 0:
            print(f"   - '{k}': {c:,} hits")
    print(f"   Total potential noise hits: {total_noise:,} ({total_noise/total_count*100:.2f}%)")
    print("-" * 50)
    print(f"4. Random Sampling (Visual Check):")
    for i, s in enumerate(samples, 1):
        print(f"   {i:2}. {s[0]} | {s[1]} | {s[2]}")
        print(f"       [Vectors] E:{s[3]:.2f} O:{s[4]:.2f} S:{s[5]:.2f} R:{s[6]:.2f}")
    print("-" * 50)
    
    conn.close()

if __name__ == "__main__":
    profile()
