import sqlite3
import pandas as pd
import os

DB_PATH = "lemma_manga.db"

def ingest_csv(conn, file_path, source_name, era_val, origin_val, style_val, renown_val):
    if not os.path.exists(file_path):
        print(f"Skip: {file_path} not found.")
        return 0
    
    # engine='python' to handle quoting issues better, encoding='utf-8'
    try:
        df = pd.read_csv(file_path, encoding='utf-8', quotechar='"', skipinitialspace=True)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

    cursor = conn.cursor()
    count = 0
    
    for _, row in df.iterrows():
        try:
            title = str(row["Title"] if "Title" in row else row.iloc[0]).strip()
            author = str(row["Author"] if "Author" in row else row.iloc[1]).strip()
            
            if title == "nan" or not title: continue

            cursor.execute("""
                INSERT OR IGNORE INTO manga (title, author, source, era, origin, style, renown)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, author, source_name, era_val, origin_val, style_val, renown_val))
            if cursor.rowcount > 0:
                count += 1
        except: continue
            
    conn.commit()
    print(f"Ingested {count} records from {file_path} as '{source_name}'")
    return count

def main():
    conn = sqlite3.connect(DB_PATH)
    
    # Phase 3 Expansion
    ingest_csv(conn, "awards_history.csv", "このマンガがすごい！_過去分", 0.85, 0.0, 0.5, 0.9)
    ingest_csv(conn, "media_arts_history.csv", "文化庁メディア芸術祭", 0.6, 0.4, 0.5, 0.9)
    
    # Phase 4 Labels
    ingest_csv(conn, "afternoon_works.csv", "月刊アフタヌーン", 0.7, 0.8, 0.5, 0.6)
    ingest_csv(conn, "comic_beam_works.csv", "月刊コミックビーム", 0.7, 0.8, 0.8, 0.6)
    
    # Check total
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM manga")
    total = cursor.fetchone()[0]
    print(f"\n--- SUCCESS ---")
    print(f"Total Database Records: {total}")
    
    conn.close()

if __name__ == "__main__":
    main()
