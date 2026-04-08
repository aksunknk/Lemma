import sqlite3

conn = sqlite3.connect('C:/Users/aksak/lemma_project_core/books.db')
c = conn.cursor()

c.execute("SELECT count(*) FROM books WHERE category='wikipedia'")
count = c.fetchone()[0]

c.execute("SELECT title FROM books WHERE category='wikipedia' ORDER BY RANDOM() LIMIT 10")
titles = [r[0] for r in c.fetchall()]

with open('C:/Users/aksak/lemma_project_core/wiki_stats.txt', 'w', encoding='utf-8') as f:
    f.write(f"COUNT: {count}\n")
    for t in titles:
        f.write(f"- {t}\n")
