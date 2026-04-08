import requests

def test_api():
    endpoint = "https://openapi.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    app_id = "1e8295a9-d120-4d69-8858-5a7dd47de0ed"
    access_key = "pk_wASmVrd9ypC5uVs3OpAoIVRJpi11ZX0rLiFiJh53ehX"
    
    headers = {'Referer': 'http://example.com/'}
    
    combinations = [
        {"applicationId": app_id, "accessKey": access_key},
        {"application_id": app_id, "access_key": access_key},
    ]
    
    for i, params in enumerate(combinations):
        params.update({"format": "json", "title": "あ"})
        print(f"Test {i+1} with params: {list(params.keys())}")
        try:
            res = requests.get(endpoint, params=params, headers=headers, timeout=5)
            print(f"Status: {res.status_code}")
            print(f"Body: {res.text}")
        except Exception as e:
            print(f"Error: {e}")
        print("-" * 20)

if __name__ == "__main__":
    test_api()
