import sqlite3
import os

conn = sqlite3.connect('C:/Users/aksak/lemma_project_core/books.db')
c = conn.cursor()

c.execute("SELECT count(*) FROM books WHERE category='aozora'")
count = c.fetchone()[0]

c.execute("SELECT title FROM books WHERE category='aozora' ORDER BY rowid ASC")
titles = [r[0] for r in c.fetchall()]

out_text = f"青空文庫CSVから抽出された「真の総登録件数」: {count}件\n"
if titles:
    out_text += "先頭のタイトル:\n"
    for t in titles[:3]: out_text += f"- {t}\n"
    out_text += "末尾のタイトル:\n"
    for t in titles[-2:]: out_text += f"- {t}\n"

exclusions = ""
try:
    with open('C:/Users/aksak/lemma_project_core/aozora_new_out.txt', 'r', encoding='utf-16le') as f:
        text = f.read()
    for line in text.splitlines():
        if '除外要因' in line:
            exclusions = line.replace('【除外要因】', '').strip()
            # Also replace commas with line breaks? No, just keep the line.
except Exception as e:
    exclusions = str(e)

out_text += f"除外されたデータの主な傾向（1行のみ）: {exclusions}\n"

with open('C:/Users/aksak/lemma_project_core/final_stats.txt', 'w', encoding='utf-8') as f:
    f.write(out_text)
