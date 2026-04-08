import sqlite3
import unicodedata

DB_PATH = "lemma_manga.db"

def normalize_text(text):
    if not text: return ""
    # Unicode NFKC normalization (Full-width to Half-width for alphanumeric)
    text = unicodedata.normalize('NFKC', text)
    # Strip whitespace
    return text.strip()

def finalize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- Starting Normalization ---")
    cursor.execute("SELECT id, title, author FROM manga")
    rows = cursor.fetchall()
    
    update_count = 0
    for row_id, title, author in rows:
        n_title = normalize_text(title)
        n_author = normalize_text(author)
        if n_title != title or n_author != author:
            cursor.execute("UPDATE manga SET title = ?, author = ? WHERE id = ?", (n_title, n_author, row_id))
            update_count += 1
    
    conn.commit()
    print(f"Normalized {update_count} records (Whitespace/Width).")

    print("\n--- Starting Deduplication ---")
    # Identify duplicates based on normalized Title + Author
    # We keep the one with the smallest ID (usually the first ingested/primary source)
    cursor.execute("""
        DELETE FROM manga
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM manga
            GROUP BY title, author
        )
    """)
    deleted_count = cursor.rowcount
    conn.commit()
    print(f"Removed {deleted_count} duplicate records.")

    print("\n--- Starting Vector Validation ---")
    cursor.execute("SELECT id, era, origin, style, renown FROM manga")
    rows = cursor.fetchall()
    
    clamp_count = 0
    for row_id, era, origin, style, renown in rows:
        def clamp(val):
            if val is None: return 0.5
            return max(0.0, min(1.0, float(val)))
        
        n_era = clamp(era)
        n_origin = clamp(origin)
        n_style = clamp(style)
        n_renown = clamp(renown)
        
        if (n_era != era or n_origin != origin or 
            n_style != style or n_renown != renown):
            cursor.execute("""
                UPDATE manga 
                SET era = ?, origin = ?, style = ?, renown = ? 
                WHERE id = ?
            """, (n_era, n_origin, n_style, n_renown, row_id))
            clamp_count += 1
            
    conn.commit()
    print(f"Validated/Clamped {clamp_count} vector sets.")

    # Final Count
    cursor.execute("SELECT COUNT(*) FROM manga")
    total = cursor.fetchone()[0]
    print(f"\nFinal record count: {total}")
    
    conn.close()

if __name__ == "__main__":
    finalize_database()
