import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_test_scenario(name, payload):
    print(f"\n--- Scenario: {name} ---")
    response = client.post("/api/search", json=payload)
    print(f"HTTP Status: {response.status_code}")
    data = response.json()
    print(f"Response Body: {json.dumps(data, indent=2, ensure_ascii=False)}")
    if response.status_code == 200:
        print(f"Category: {data.get('category')}")
        print(f"Title: {data.get('title')}")
        print(f"Distance: {data.get('distance')}")
    else:
        print(f"Error Detail: {data.get('detail')}")

if __name__ == "__main__":
    # 1. マンガ抽出テスト (近現代・国内・高知名度)
    # 既存のアワード作品（例: 消えた初恋 等）がヒットする領域
    run_test_scenario("Manga Retrieval", {
        "era_min": 0.8, "era_max": 1.0, 
        "origin": 0.0, "style": 0.5, "renown": 0.9
    })

    # 2. 活字本抽出テスト (古典・国内・スタンダード・高知名度)
    # 夏目漱石等の活字本がヒットしやすい空間
    run_test_scenario("Book Retrieval", {
        "era_min": 0.0, "era_max": 0.2, 
        "origin": 0.1, "style": 0.9, "renown": 0.8
    })

    # 3. 誠実な沈黙テスト (防壁検証)
    # 座標が乖離しており、かつ閾値0.3を超える空間（意図的なスカ）
    run_test_scenario("Sincere Silence (404)", {
        "era_min": 0.5, "era_max": 0.5, 
        "origin": 0.5, "style": 0.5, "renown": 0.0
    })
