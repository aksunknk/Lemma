import requests
from sqlalchemy.orm import Session
from models import Book
from .text_analysis import calculate_style_score

def fetch_books_from_api(query: str, max_results: int = 15):
    # 日本語の書籍を中心に取得
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={max_results}&langRestrict=ja"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get('items', [])
    except Exception as e:
        print(f"Error fetching from Google Books API: {e}")
    return []

def hydrate_database_if_empty(db: Session):
    if db.query(Book).first():
        return
        
    print("Hydrating database with initial seed...")
    
    queries = [
        {"q": "subject:fiction", "era": 2000, "domestic": True},
        {"q": "夏目漱石", "era": 1905, "domestic": True},
        {"q": "Dostoevsky", "era": 1866, "domestic": False},
        {"q": "JavaScript", "era": 2023, "domestic": False},
        {"q": "ハリーポッター", "era": 1997, "domestic": False},
    ]
    
    for q_info in queries:
        items = fetch_books_from_api(q_info["q"], max_results=10)
        for item in items:
            v_info = item.get('volumeInfo', {})
            vid = item.get('id')
            title = v_info.get('title', 'Unknown')
            authors = v_info.get('authors', ['Unknown'])
            desc = v_info.get('description', '')
            image_links = v_info.get('imageLinks', {})
            image_url = image_links.get('thumbnail', '')
            
            style = calculate_style_score(desc)
            ratings_count = v_info.get('ratingsCount', 0)
            
            popularity = min(1.0, ratings_count / 100.0)
            if popularity == 0:
                # ページ数などを代替にする、または0.5
                page_count = v_info.get('pageCount', 0)
                popularity = min(1.0, page_count / 500.0)
                
            pub_date = v_info.get('publishedDate', '')
            era = q_info["era"]
            if pub_date:
                try:
                    era = int(pub_date.split('-')[0])
                except Exception:
                    pass
            
            if not db.query(Book).filter(Book.id == vid).first():
                b = Book(
                    id=vid,
                    title=title,
                    author=authors[0],
                    description=desc,
                    image_url=image_url,
                    era=era,
                    origin_domestic=q_info["domestic"],
                    popularity=popularity,
                    style_score=style
                )
                db.add(b)
    db.commit()
    print("Hydration complete.")
