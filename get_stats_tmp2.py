import sqlite3
import random

conn = sqlite3.connect('C:/Users/aksak/lemma_project_core/books.db')
c = conn.cursor()

c.execute("SELECT count(*) FROM books WHERE category='aozora'")
current_total = c.fetchone()[0]
new_count = current_total - 12023

c.execute("SELECT title FROM books WHERE category='aozora' AND style_score=0.1 ORDER BY RANDOM() LIMIT 10")
philosophy_samples = [r[0] for r in c.fetchall()]

out_text = f"青空文庫から books.db に「新規追加（差分登録）」された総件数: {new_count}件\n"
if philosophy_samples:
    out_text += "登録されたタイトルのサンプル:\n"
    for s in philosophy_samples:
        out_text += f"  - {s}\n"

with open('C:/Users/aksak/lemma_project_core/stats_out2.txt', 'w', encoding='utf-8') as f:
    f.write(out_text)
