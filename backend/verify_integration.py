import json
from vector_search import LemmaSearchEngine

def verify():
    engine = LemmaSearchEngine()
    df = engine.df
    print(f"Total entries: {len(df)}")
    print(f"Books count: {len(df[df['category'] == 'book'])}")
    print(f"Manga count: {len(df[df['category'] == 'manga'])}")
    
    # 統合検索のテスト
    target = [0.8, 0.0, 0.5, 0.8]
    result = engine.search_closest_book(target)
    print("\nSearch Result Sample:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # リターン構造の不備がないか確認
    required_keys = ["status", "item_id", "title", "author", "source", "category", "distance", "vector"]
    if result["status"] == 200:
        for key in required_keys:
            if key not in result:
                print(f"MISSING KEY: {key}")
            else:
                print(f"{key}: OK")

if __name__ == "__main__":
    verify()
