import json
import random
import os

def inspect_json():
    file_path = "raw_books_10000.json"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Noneではない有効なデータをフィルタリング
        valid_books = [book for book in data if book is not None]
        
        if not valid_books:
            print("No valid book data found in the JSON.")
            return
            
        # ランダムに1件取得
        book = random.choice(valid_books)
        
        summary = book.get("summary", {})
        onix = book.get("onix", {})
        
        title = summary.get("title", "N/A")
        author = summary.get("author", "N/A")
        publisher = summary.get("publisher", "N/A")
        
        # Cコードの抽出 (SubjectSchemeIdentifier '78')
        c_code = "N/A"
        subjects = onix.get("DescriptiveDetail", {}).get("Subject", [])
        for sub in subjects:
            if sub.get("SubjectSchemeIdentifier") == "78":
                c_code = sub.get("SubjectCode", "N/A")
                break
        
        # あらすじの抽出 (TextType '03')
        description = "N/A"
        collateral = onix.get("CollateralDetail", {})
        texts = collateral.get("TextContent", [])
        for t in texts:
            if t.get("TextType") == "03":
                description = t.get("Text", "N/A")
                break
        
        if description == "N/A":
            # hanmotoデータからも探す
            description = book.get("hanmoto", {}).get("aisatsu", "N/A")
            if description == "N/A":
                description = book.get("hanmoto", {}).get("hikiai_yomi", "N/A")

        print(f"Title: {title}")
        print(f"Author: {author}")
        print(f"Publisher: {publisher}")
        print(f"C-Code: {c_code}")
        print(f"Description (First 100 chars): {description[:100]}...")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_json()
