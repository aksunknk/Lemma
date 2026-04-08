import sqlite3
import os

db_path = "c:\\Users\\Panasonic\\.gemini\\antigravity\\scratch\\single-book-engine\\books.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            print(f"Columns in {table_name}: {cursor.fetchall()}")
            cursor.execute(f"SELECT count(*) FROM {table_name};")
            print(f"Count in {table_name}: {cursor.fetchone()[0]}")
            
            cursor.execute(f"SELECT category, count(*) FROM {table_name} GROUP BY category;")
            print(f"Category counts: {cursor.fetchall()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
