import requests
import random
import json
import sys

def fetch_raw_books():
    coverage_url = "https://api.openbd.jp/v1/coverage"
    get_url = "https://api.openbd.jp/v1/get"
    output_file = "raw_books_10000.json"
    
    try:
        # 1. coverage APIから全ISBNリストを取得
        print("Fetching coverage list...")
        response = requests.get(coverage_url, timeout=30)
        response.raise_for_status()
        all_isbns = response.json()
        
        # 2. 10,000件をランダムサンプリング
        print(f"Sampling 10,000 ISBNs from {len(all_isbns)} items...")
        sample_size = min(10000, len(all_isbns))
        sampled_isbns = random.sample(all_isbns, sample_size)
        
        # 3. バルクAPIで詳細データを取得 (1回のリクエスト)
        print("Fetching bulk data from openBD...")
        # POSTリクエストでISBNを送る（件数が多い場合はPOSTが安定する）
        payload = {"isbn": ",".join(sampled_isbns)}
        response = requests.post(get_url, data=payload, timeout=60)
        response.raise_for_status()
        raw_data = response.json()
        
        # 4. 生のJSONデータを保存
        print(f"Saving raw data to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
            
        print("Success.")
        
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    fetch_raw_books()
