import sqlite3
conn = sqlite3.connect('books.db')
c = conn.cursor()
c.execute("SELECT id, title, author, era, popularity, style_score, substr(description, 1, 60) FROM books WHERE category='aozora'")
rows = c.fetchall()
for r in rows:
    print(f"{r[1]} / {r[2]} | era={r[3]} pop={r[4]} style={r[5]}")
    print(f"  text: {r[6]}...")
print(f"\n合計: {len(rows)} 件")
c.execute("SELECT COUNT(*) FROM books")
print(f"DB全体: {c.fetchone()[0]} 件")
conn.close()
