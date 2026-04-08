import sqlite3

conn = sqlite3.connect('C:/Users/aksak/lemma_project_core/books.db')
c = conn.cursor()

c.execute("SELECT count(*) FROM books WHERE category='aozora'")
count_total = c.fetchone()[0]

try:
    with open('C:/Users/aksak/lemma_project_core/new_aozora_out.txt', 'r', encoding='utf-16le', errors='ignore') as f:
        text = f.read()
except:
    text = ""
    
lines = text.splitlines()
new_count = 0
samples = []
for line in lines:
    if line.startswith("NEW_COUNT:"):
        new_count = int(line.replace("NEW_COUNT:", "").strip())
    elif line.startswith("SAMPLE:"):
        samples.append(line.replace("SAMPLE:", "").strip())

out_text = f"青空文庫から books.db に「新規追加（差分登録）」された総件数: {new_count}件\n"
if samples:
    out_text += "登録されたタイトルのサンプル:\n"
    for s in samples:
        out_text += f"  - {s}\n"

with open('C:/Users/aksak/lemma_project_core/stats_out.txt', 'w', encoding='utf-8') as f:
    f.write(out_text)
