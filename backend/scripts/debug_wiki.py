import requests
import json
import time

WIKI_API_URL = "https://ja.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "SingleBookEngineBot/1.0 (contact: your-email@example.com)"}
AUTHOR = "フョードル・ドストエフスキー"

def debug_author_search(author):
    print(f"--- Debugging: {author} ---")
    
    # カテゴリメンバー検索
    cat_name = f"{author}の作品"
    params = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": f"Category:{cat_name}",
        "cmlimit": 10
    }
    print(f"1. Category search for: Category:{cat_name}")
    try:
        r = requests.get(WIKI_API_URL, params=params, headers=HEADERS)
        print(f"Response Status: {r.status_code}")
        data = r.json()
        members = data.get("query", {}).get("categorymembers", [])
        print(f"Found {len(members)} members:")
        for m in members:
            print(f"  - {m['title']} (NS: {m['ns']})")
    except Exception as e:
        print(f"Error: {e}")

    # 通常のリスト検索
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": f"{author} 作品",
        "srlimit": 5
    }
    print(f"\n2. Search list for: {author} 作品")
    try:
        r = requests.get(WIKI_API_URL, params=params, headers=HEADERS)
        data = r.json()
        results = data.get("query", {}).get("search", [])
        print(f"Found {len(results)} results:")
        for res in results:
            print(f"  - {res['title']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_author_search(AUTHOR)
    debug_author_search("魯迅")
