import requests
import json
import sys

def test_poc():
    public_url = "https://aviation-electron-ted-gave.trycloudflare.com"
    endpoint = f"{public_url}/api/search"
    
    # 修正後のリクエストデータ（era_min, era_max を使用）
    test_payload = {
        "era_min": 0.4,
        "era_max": 0.6,
        "origin": 1.0,
        "style": 0.8,
        "renown": 1.0,
        "keyword": None
    }
    
    print(f"Testing public URL: {endpoint}")
    try:
        response = requests.post(
            endpoint, 
            json=test_payload, 
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        print("Response Data:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200:
            print("\nConclusion: The local API is successfully accessible from the public internet.")
        else:
            print(f"\nConclusion: Connection made, but status code is {response.status_code}.")
            
    except Exception as e:
        print(f"Test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_poc()
