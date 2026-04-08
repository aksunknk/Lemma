import pandas as pd
import sys

# Windows環境での日本語表示対応
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

targets = [
    {"name": "マンガ大賞", "url": "https://ja.wikipedia.org/wiki/%E3%83%9E%E3%83%B3%E3%82%AC%E5%A4%A7%E8%B3%9E"},
    {"name": "このマンガがすごい！", "url": "https://ja.wikipedia.org/wiki/%E3%81%93%E3%81%AE%E3%83%9E%E3%83%B3%E3%82%AC%E3%81%8C%E3%81%99%E3%81%94%E3%81%84!"},
    {"name": "次にくるマンガ大賞", "url": "https://ja.wikipedia.org/wiki/%E6%AC%A1%E3%81%AB%E3%81%8F%E3%82%8B%E3%83%9E%E3%83%B3%E3%82%AC%E5%A4%A7%E8%B3%9E"},
    {"name": "文化庁メディア芸術祭", "url": "https://ja.wikipedia.org/wiki/%E6%96%87%E5%8C%96%E5%BA%81%E3%83%A1%E3%83%87%E3%82%A3%E3%82%A2%E8%8A%B8%E8%A1%93%E7%A5%AD"},
]

for t in targets:
    print(f"\n--- Investigating: {t['name']} ---")
    try:
        tables = pd.read_html(t['url'])
        print(f"Total tables found: {len(tables)}")
        for i, df in enumerate(tables[:15]):
            cols = df.columns
            if isinstance(cols, pd.MultiIndex):
                # 階層化されている場合
                flattened = [' | '.join(map(str, col)).strip() for col in cols.values]
                print(f"Table {i} (Multi): {flattened[:5]}")
            else:
                print(f"Table {i}: {list(cols)[:5]}")
    except Exception as e:
        print(f"Error: {e}")
