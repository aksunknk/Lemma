import sqlite3
import os
import sys

# 標準出力を UTF-8 に設定
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def check_quadrants():
    db_path = "books.db"
    if not os.path.exists(db_path):
        print("エラー: books.db が見つかりません。")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 4次元ベクトルのうち「海外度（origin_domestic）」と「平易度（style_score）」を使用
        cursor.execute("SELECT title, origin_domestic, style_score FROM books")
        rows = cursor.fetchall()
        
        # 象限の定義（閾値0.5）
        # 第1象限: 海外(f>=0.5)・平易(p>=0.5)
        # 第2象限: 国内(f<0.5)・平易(p>=0.5)
        # 第3象限: 国内(f<0.5)・硬質(p<0.5)
        # 第4象限: 海外(f>=0.5)・硬質(p<0.5)
        quadrants = {
            "第一象限 (海外・平易)": [],
            "第二象限 (国内・平易)": [],
            "第三象限 (国内・硬質)": [],
            "第四象限 (海外・硬質)": []
        }
        
        for row in rows:
            title, f_score, p_score = row
            # f_score (origin_domestic) は 0 or 1 だが、小数の場合も考慮
            f_score = float(f_score) if f_score is not None else 0.0
            p_score = float(p_score) if p_score is not None else 0.5
            
            if f_score >= 0.5 and p_score >= 0.5:
                quadrants["第一象限 (海外・平易)"].append(title)
            elif f_score < 0.5 and p_score >= 0.5:
                quadrants["第二象限 (国内・平易)"].append(title)
            elif f_score < 0.5 and p_score < 0.5:
                quadrants["第三象限 (国内・硬質)"].append(title)
            else:
                quadrants["第四象限 (海外・硬質)"].append(title)
        
        print(f"現在の登録総数: {len(rows)}件\n")
        print("【ベクトル空間 分布状況】")
        for q, titles in quadrants.items():
            print(f"■ {q}: {len(titles)}件")
            for t in titles[:10]:  # 各象限最大10件まで表示
                print(f"  - {t}")
            if len(titles) > 10:
                print(f"  ...他 {len(titles)-10}件")
            print()
                
    except Exception as e:
        print(f"データベース実行エラー: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_quadrants()
