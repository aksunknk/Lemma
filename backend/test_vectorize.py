import sqlite3

def get_style(publisher):
    academic = ["岩波書店", "筑摩書房", "平凡社", "みすず書房", "東京大学出版会"]
    return 0.8 if any(a in publisher for a in academic) else 0.5

def get_renown(publisher):
    major = ["講談社", "集英社", "KADOKAWA", "小学館", "文藝春秋", "新潮社"]
    return 0.9 if any(m in publisher for m in major) else 0.5

def test_vectorize():
    conn = sqlite3.connect('new_books_2024_2026.db')
    cursor = conn.cursor()
    cursor.execute("SELECT isbn, title, publisher FROM cleaned_books LIMIT 5")
    rows = cursor.fetchall()
    
    print("| ISBN | TITLE | PUBLISHER | VECTOR [E, O, S, R] |")
    print("| :--- | :--- | :--- | :--- |")
    
    for isbn, title, publisher in rows:
        era = 1.0
        origin = 0.0
        style = get_style(publisher)
        renown = get_renown(publisher)
        
        vec_str = f"[{era:.1f}, {origin:.1f}, {style:.1f}, {renown:.1f}]"
        print(f"| {isbn} | {title[:30]} | {publisher} | {vec_str} |")

    conn.close()

if __name__ == "__main__":
    test_vectorize()
