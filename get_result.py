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

print("NAROU COUNT:", narou_count)
print("NAROU TITLES:", narou_titles)
print("AOZORA COUNT:", aozora_count)
print("AOZORA TITLES:", aozora_titles)
