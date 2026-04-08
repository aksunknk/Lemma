import sqlite3
import os

def inspect_raw():
    db_path = "books.db"
    if not os.path.exists(db_path):
        print("エラー books.db が見つかりません。")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 生データの抽出（異常値の確認のため、日本の古典を含む先頭20件を取得）
        query = "SELECT id, title, origin_domestic AS foreign_score, style_score AS plain_score, popularity AS niche_score FROM books LIMIT 20"
        cursor.execute(query)

        rows = cursor.fetchall()
        
        print(f"{'ID':<4} | {'タイトル':<30} | {'海外':<5} | {'平易':<5} | {'ニッチ':<5}")
        print("-" * 60)
        for row in rows:
            print(f"{str(row[0]):<4} | {str(row[1])[:28]:<30} | {row[2]:<5} | {row[3]:<5} | {row[4]:<5}")
                
        conn.close()
    except Exception as e:
        print(f"実行エラー {e}")

if __name__ == "__main__":
    inspect_raw()
