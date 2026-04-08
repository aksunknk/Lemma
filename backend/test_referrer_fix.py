import requests
import time

def test_referrer():
    endpoint = "https://openapi.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    app_id = "1e8295a9-d120-4d69-8858-5a7dd47de0ed"
    access_key = "pk_wASmVrd9ypC5uVs3OpAoIVRJpi11ZX0rLiFiJh53ehX"
    
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "format": "json",
        "title": "あ"
    }

    tests = [
        ("One R", {'Referer': 'http://example.com/'}),
        ("Two Rs", {'Referrer': 'http://example.com/'}),
        ("Both", {'Referer': 'http://example.com/', 'Referrer': 'http://example.com/'})
    ]

    for name, headers in tests:
        print(f"Testing {name}...")
        try:
            res = requests.get(endpoint, params=params, headers=headers, timeout=5)
            print(f"Status: {res.status_code}")
            print(f"Body: {res.text[:100]}...")
            if res.status_code == 200:
                print("SUCCESS!")
                break
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(2) # Avoid immediate rate limit
        print("-" * 20)

if __name__ == "__main__":
    test_referrer()
