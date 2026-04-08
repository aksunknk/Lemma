import sqlite3
import re
import os

DB_PATH = "openbd_supplement.db"
DELETE_KEYWORDS = ['セット', '特装版', '初回限定', 'DVD付', 'CD付', '公式ガイド', 'カレンダー', '手帳', 'ダイアリー']

def clean_text(text):
    if not text:
        return text
    # HTMLタグの除去
    text = re.sub(r'<[^>]+>', '', text)
    # 全角スペース、タブをスペースに置換
    text = text.replace('　', ' ').replace('\t', ' ')
    # 連続する改行を単一改行へ
    text = re.sub(r'\n\n+', '\n', text)
    # 連続するスペースを単一スペースへ
    text = re.sub(r'  +', ' ', text)
    # トリム
    return text.strip()

def cleanse():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 0. 初期カウント
    cursor.execute("SELECT COUNT(*) FROM books")
    initial_count = cursor.fetchone()[0]

    # 1. ノイズレコードの物理削除
    deleted_total = 0
    for keyword in DELETE_KEYWORDS:
        cursor.execute("DELETE FROM books WHERE title LIKE ?", (f'%{keyword}%',))
        deleted_total += cursor.rowcount
    
    conn.commit()

    # 2. あらすじの正規化
    # メモリ効率のため、1000件ずつ取得して更新
    cursor.execute("SELECT isbn, description FROM books WHERE description IS NOT NULL AND description != ''")
    records = cursor.fetchall()
    
    updated_count = 0
    for isbn, desc in records:
        cleaned_desc = clean_text(desc)
        if cleaned_desc != desc:
            cursor.execute("UPDATE books SET description = ? WHERE isbn = ?", (cleaned_desc, isbn))
            updated_count += 1
            
        if updated_count % 10000 == 0 and updated_count > 0:
            conn.commit()
            print(f"Processed {updated_count} updates...")

    conn.commit()

    # 3. 最終カウント
    cursor.execute("SELECT COUNT(*) FROM books")
    final_count = cursor.fetchone()[0]

    # 4. 真空パック (Database compaction)
    print("Compacting database (VACUUM)...")
    conn.execute("VACUUM")
    conn.close()

    # 結果出力
    print("-" * 50)
    print("=== [lemma] Data Cleansing Result ===")
    print("-" * 50)
    print(f"Initial Records: {initial_count:,}")
    print(f"Deleted Records: {deleted_total:,}")
    print(f"Updated Records: {updated_count:,} (Normalized descriptions)")
    print(f"Final Records:   {final_count:,}")
    print("-" * 50)

if __name__ == "__main__":
    cleanse()
