import sqlite3
import json

conn = sqlite3.connect('C:/Users/aksak/lemma_project_core/books.db')
c = conn.cursor()

c.execute("SELECT count(*) FROM books WHERE category='NAROU'")
narou_count = c.fetchone()[0]

c.execute("SELECT title FROM books WHERE category='NAROU' LIMIT 5")
narou_titles = [r[0] for r in c.fetchall()]

c.execute("SELECT count(*) FROM books WHERE category='aozora'")
aozora_count = c.fetchone()[0]

c.execute("SELECT title FROM books WHERE category='aozora' LIMIT 5")
aozora_titles = [r[0] for r in c.fetchall()]

with open("C:/Users/aksak/lemma_project_core/result_final.txt", "w", encoding="utf-8") as f:
    f.write(f"NAROU COUNT: {narou_count}\n")
    f.write("NAROU TITLES:\n")
    for t in narou_titles: f.write(f"- {t}\n")
    f.write(f"AOZORA COUNT: {aozora_count}\n")
    f.write("AOZORA TITLES:\n")
    for t in aozora_titles: f.write(f"- {t}\n")
