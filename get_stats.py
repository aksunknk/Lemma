import sqlite3
import os

conn = sqlite3.connect('C:/Users/aksak/lemma_project_core/books.db')
c = conn.cursor()

c.execute("SELECT count(*) FROM books WHERE category='aozora'")
count = c.fetchone()[0]

c.execute("SELECT title FROM books WHERE category='aozora' ORDER BY rowid ASC")
titles = [r[0] for r in c.fetchall()]

print(f"TOTAL: {count}")
if titles:
    print(f"FIRST: {titles[:3]}")
    print(f"LAST:  {titles[-2:]}")
else:
    print("No Aozora entries found.")

try:
    with open('C:/Users/aksak/lemma_project_core/aozora_new_out.txt', 'r', encoding='utf-16le') as f:
        text = f.read()
    for line in text.splitlines():
        if '除外要因' in line:
            print(line)
except Exception as e:
    print("Error reading out file:", e)
