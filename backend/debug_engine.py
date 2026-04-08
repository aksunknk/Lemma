import sqlite3
import pandas as pd
import os
import time
import traceback

def test_load():
    db_path = "lemma_master.db"
    manga_db_path = "lemma_manga.db"
    new_books_db_path = "lemma_new_books.db"
    
    print(f"Connecting to {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if os.path.exists(manga_db_path):
            print(f"Attaching {manga_db_path}...")
            cursor.execute(f"ATTACH DATABASE '{manga_db_path}' AS manga_db")
        if os.path.exists(new_books_db_path):
            print(f"Attaching {new_books_db_path}...")
            cursor.execute(f"ATTACH DATABASE '{new_books_db_path}' AS new_books")
            
        queries = [
            "SELECT isbn as item_id, title, author, publisher as source, era, origin, style, renown, 'book' as category FROM books",
        ]
        if os.path.exists(manga_db_path):
            queries.append("SELECT CAST(id AS TEXT) as item_id, title, author, source, era, origin, style, renown, 'manga' as category FROM manga_db.manga")
        if os.path.exists(new_books_db_path):
            queries.append("SELECT isbn as item_id, title, author, publisher as source, era, origin, style, renown, category FROM new_books.books")
            
        query = " UNION ALL ".join(queries)
        print("Executing UNION ALL and loading into Pandas (This may take over 60 seconds)...")
        start = time.time()
        df = pd.read_sql_query(query, conn)
        end = time.time()
        print(f"SUCCESS: Loaded {len(df)} records in {round(end-start, 2)} seconds.")
        conn.close()
    except Exception as e:
        print("FAILED to load data.")
        traceback.print_exc()

if __name__ == "__main__":
    test_load()
