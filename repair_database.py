import sqlite3
import sys

def main():
    db_path = r'C:\Users\aksak\lemma_project_core\books.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check total nulls before
    cursor.execute("SELECT COUNT(*) FROM books WHERE foreign_score IS NULL OR plain_score IS NULL")
    initial_nulls = cursor.fetchone()[0]
    print(f"Initial NULL count: {initial_nulls}")
    
    # 1. Narou (ncode starts with n, or category indicates narou)
    cursor.execute("""
        UPDATE books 
        SET foreign_score = 0.0, plain_score = 0.9 
        WHERE (foreign_score IS NULL OR plain_score IS NULL) 
          AND (ncode LIKE 'n%' OR ncode LIKE 'N%' OR category LIKE '%NAROU%')
    """)
    updated_narou = cursor.rowcount
    
    # 2. Wikidata / Wikipedia (ncode starts with Q or WIKI)
    cursor.execute("""
        UPDATE books 
        SET foreign_score = 1.0, plain_score = 0.1 
        WHERE (foreign_score IS NULL OR plain_score IS NULL) 
          AND (ncode LIKE 'Q%' OR ncode LIKE 'WIKI%' OR category LIKE '%WIKI%' OR id LIKE 'WIKI%')
    """)
    updated_wiki = cursor.rowcount
    
    # 3. Aozora
    cursor.execute("""
        UPDATE books 
        SET foreign_score = 0.0, plain_score = 0.2 
        WHERE (foreign_score IS NULL OR plain_score IS NULL) 
          AND (category LIKE '%AOZORA%' OR ncode LIKE 'aozora%')
    """)
    updated_aozora = cursor.rowcount
    
    # 4. Fallback for any remaining unclassified NULLs 
    # (assuming they might be domestic literature or NDL stuff not fully scored)
    cursor.execute("""
        UPDATE books 
        SET foreign_score = 0.5, plain_score = 0.5 
        WHERE (foreign_score IS NULL OR plain_score IS NULL)
    """)
    updated_fallback = cursor.rowcount
    
    # 5. renown_score NULL handling
    cursor.execute("""
        UPDATE books 
        SET renown_score = 0.0 
        WHERE renown_score IS NULL
    """)
    updated_renown = cursor.rowcount
    
    conn.commit()
    
    # Check total after
    cursor.execute("SELECT COUNT(*) FROM books WHERE foreign_score IS NOT NULL AND plain_score IS NOT NULL")
    valid_total = cursor.fetchone()[0]
    
    print(f"Updated Narou: {updated_narou}")
    print(f"Updated Wiki: {updated_wiki}")
    print(f"Updated Aozora: {updated_aozora}")
    print(f"Updated Fallback: {updated_fallback}")
    print(f"Updated Renown: {updated_renown}")
    print(f"Valid Total: {valid_total}")
    
    conn.close()

if __name__ == "__main__":
    main()
