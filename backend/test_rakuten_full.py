import requests

def test_full():
    endpoint = "https://openapi.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    app_id = "1e8295a9-d120-4d69-8858-5a7dd47de0ed"
    access_key = "pk_wASmVrd9ypC5uVs3OpAoIVRJpi11ZX0rLiFiJh53ehX"
    
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "format": "json",
        "booksGenreId": "001004",
        "title": "あ",
        "page": 1,
        "hits": 30,
        "sort": "standard"
    }
    
    headers = {'Referer': 'http://example.com/'}
    
    print("Testing with full params...")
    try:
        res = requests.get(endpoint, params=params, headers=headers, timeout=5)
        print(f"Status: {res.status_code}")
        print(f"Body: {res.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_full()
