import sys
import time
import json
import sqlite3
import urllib.request
from datetime import datetime
import random

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\aksak\lemma_project_core\books.db'
BASE_URL = "https://api.syosetu.com/novelapi/api/?out=json&lim=500&order=lastup"

HARD_WORDS = ['講義', '評論', '研究', '哲学', '存在論', '思想', '論理', '年鑑', '白書', 'シラバス', '総目次', '索引']

TARGET_COUNT = 20000
MAX_LOOPS = 40
MIN_LENGTH = 10000

FOREIGN_SCORE = 0.0
PLAIN_SCORE = 0.9


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_added = 0
    loop_count = 0
    added_titles = []
    lastup_param = ""

    while total_added < TARGET_COUNT and loop_count < MAX_LOOPS:
        loop_count += 1
        url = BASE_URL + lastup_param

        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            with urllib.request.urlopen(req, timeout=30) as res:
                data = json.loads(res.read().decode('utf-8'))
        except Exception as e:
            print(f"APIリクエスト失敗 (Loop {loop_count}): {e}")
            break

        if not data or len(data) <= 1:
            print("取得データなし。終了。")
            break

        novels = data[1:]
        new_in_loop = 0

        for novel in novels:
            ncode = novel.get('ncode')
            if not ncode:
                continue

            title = novel.get('title', '')
            story = novel.get('story', '')
            author = novel.get('writer', '')
            length = novel.get('length', 0)

            if length < MIN_LENGTH:
                continue

            combined_text = title + " " + story
            if any(w in combined_text for w in HARD_WORDS):
                continue

            firstup = novel.get('general_firstup', '2000-01-01')
            era_year = 2000
            if firstup:
                try:
                    era_year = int(firstup[:4])
                except (ValueError, TypeError):
                    pass

            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO books
                    (id, title, author, description, era, origin_domestic, popularity, style_score, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ncode,
                    title,
                    author,
                    story,
                    era_year,
                    FOREIGN_SCORE,
                    PLAIN_SCORE,
                    PLAIN_SCORE,
                    'NAROU'
                ))

                if cursor.rowcount > 0:
                    total_added += 1
                    new_in_loop += 1
                    added_titles.append(title)
            except sqlite3.Error:
                pass

        conn.commit()

        print(f"Loop {loop_count}: 新規 {new_in_loop} 件 / 累計 {total_added} 件")

        oldest = novels[-1]
        gl = oldest.get('general_lastup')
        if gl:
            dt = datetime.strptime(gl, '%Y-%m-%d %H:%M:%S')
            ts = int(dt.timestamp())
            lastup_param = f"&lastup=-{ts}"
        else:
            print("general_lastup が見つかりません。終了。")
            break

        time.sleep(3)

    conn.close()

    print(f"\n=== 結果 ===")
    print(f"新規追加（差分登録）総件数: {total_added} 件")
    print(f"\n登録タイトルサンプル（ランダム10件）:")
    if added_titles:
        sample_size = min(10, len(added_titles))
        for t in random.sample(added_titles, sample_size):
            print(f"  - {t}")


if __name__ == "__main__":
    main()
