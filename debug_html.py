import urllib.request

url = "https://www.aozora.gr.jp/access_ranking/2022_xhtml.html"
req = urllib.request.Request(url, headers={"User-Agent": "Test/1.0"})
with urllib.request.urlopen(req, timeout=15) as res:
    html = res.read().decode("utf-8")

lines = html.split("\n")
# 49行目〜75行目を表示（テーブル部分）
for i in range(48, min(80, len(lines))):
    print(f"{i}: {lines[i]}")
