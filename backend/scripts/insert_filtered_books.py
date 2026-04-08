import json
import os
import sys
import sqlite3

# 標準出力を UTF-8 に再設定（cp932 エラー対策）
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def insert_filtered_books():
    json_path = "raw_books_10000.json"
    db_path = "books.db"
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        return

    major_publishers = ['講談社', '集英社', '新潮社', 'KADOKAWA', '文藝春秋', '小学館', '角川書店']
    hard_block_words = ['論証', '体系', '批判', '理性', '形而上学', '講義', '評論', '研究', '哲学', '存在論', '思想', '論理']
    entertainment_words = ['エッセイ', 'ユーモア', '日常', 'ミステリー', 'ファンタジー', '冒険', '青春', 'コメディ', '笑い', 'ほのぼの']

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    total_count = 0
    saved_count = 0
    titles_saved = []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        for item in data:
            if item is None:
                continue
            
            total_count += 1
            
            try:
                summary = item.get("summary", {})
                onix = item.get("onix", {})
                
                title = summary.get("title")
                author = summary.get("author", "")
                publisher = summary.get("publisher", "")
                isbn = summary.get("isbn")
                
                if not title or not isbn:
                    continue

                # Cコードの抽出
                c_code = None
                subjects = onix.get("DescriptiveDetail", {}).get("Subject", [])
                for sub in subjects:
                    if sub.get("SubjectSchemeIdentifier") == "78":
                        c_code = sub.get("SubjectCode")
                        break
                
                # あらすじの抽出
                description = ""
                collateral = onix.get("CollateralDetail", {})
                texts = collateral.get("TextContent", [])
                for t in texts:
                    if t.get("TextType") == "03":
                        description += t.get("Text", "")
                if not description:
                    description = item.get("hanmoto", {}).get("aisatsu", "") or item.get("hanmoto", {}).get("hikiai_yomi", "") or ""

                # --- Cコード（4桁）によるジャンル判定の適正化 ---
                if c_code:
                    c_code_str = str(c_code).strip().upper().replace('C', '')
                    if len(c_code_str) == 4 and c_code_str.isdigit():
                        subject_code = c_code_str[2:4] # 確実に3〜4桁目（主題）を取得

                        # 哲学(10番台)、歴史(20番台)、社会科学(30番台)、自然・工学系(40〜60番台)、語学(80番台)を除外
                        if subject_code[0] in ['1', '2', '3', '4', '5', '6', '8']:
                            continue
                
                word_found = False
                for word in hard_block_words:
                    if word in (title + description):
                        word_found = True
                        break
                if word_found:
                    continue

                # --- 属性フィルター・スコアリング ---
                is_foreign = False
                c_code_str = ""
                if c_code:
                    c_code_str = str(c_code).strip().upper().replace('C', '')

                if "訳" in author or (len(c_code_str) == 4 and c_code_str[3] == '9'):
                    is_foreign = True
                
                # スコア代入（海外: 1.0, 国内: 0.0）
                foreign_score = 1.0 if is_foreign else 0.0

                is_major_found = False
                for pub in major_publishers:
                    if pub in publisher:
                        is_major_found = True
                        break
                if is_major_found:
                    continue
                
                is_entertaining = False
                for word in entertainment_words:
                    if word in description:
                        is_entertaining = True
                        break
                if not is_entertaining:
                    continue

                # --- DB格納 ---
                book_id = f"OPENBD_{isbn}"
                cursor.execute("SELECT id FROM books WHERE id=?", (book_id,))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO books (id, title, author, description, image_url, era, origin_domestic, popularity, style_score, category)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        book_id, title, author, description, summary.get("cover"),
                        2024, foreign_score, 0.9, 0.8, "OPENBD_FOREIGN_PLAIN_NICHE"
                    ))
                    saved_count += 1
                    if len(titles_saved) < 5:
                        titles_saved.append(title)
            except Exception:
                continue
        
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
        conn.rollback()
    finally:
        conn.close()

    print(f"Total processed: {total_count}")
    print(f"Saved to DB: {saved_count}")
    for t in titles_saved:
        print(f"Sample Title: {t}")

if __name__ == "__main__":
    insert_filtered_books()
