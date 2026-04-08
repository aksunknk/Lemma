import requests

def test_api():
    endpoint = "https://openapi.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    app_id = "1e8295a9-d120-4d69-8858-5a7dd47de0ed"
    access_key = "pk_wASmVrd9ypC5uVs3OpAoIVRJpi11ZX0rLiFiJh53ehX"
    
    headers_list = [
        {'Referer': 'http://localhost:5173/'},
        {'Referer': 'https://webservice.rakuten.co.jp/'},
        {'Referer': 'http://example.com/', 'Referrer': 'http://example.com/'}
    ]
    
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "format": "json",
        "title": "あ"
    }
    
    for i, headers in enumerate(headers_list):
        print(f"Test {i+1} with headers: {list(headers.keys())} and values: {list(headers.values())}")
        try:
            res = requests.get(endpoint, params=params, headers=headers, timeout=5)
            print(f"Status: {res.status_code}")
            print(f"Body: {res.text}")
        except Exception as e:
            print(f"Error: {e}")
        print("-" * 20)

if __name__ == "__main__":
    test_api()
