import requests
import time
url = "https://www.googleapis.com/books/v1/volumes?q=test&maxResults=1"
print("Sending request...")
response = requests.get(url)
print("Status:", response.status_code)
if response.status_code != 200:
    print(response.headers)
    print(response.text[:200])
else:
    print("Success. Items:", len(response.json().get('items', [])))
