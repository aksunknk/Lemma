import sqlite3
import os

def audit_db(db_path):
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return
    print(f"\nAUDIT: {db_path}")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    for table in tables:
        print(f"  Table: {table}")
        c.execute(f"PRAGMA table_info({table})")
        columns = c.fetchall()
        for col in columns:
            print(f"    {col}")
    conn.close()

if __name__ == "__main__":
    audit_db("lemma_master.db")
    audit_db("lemma_manga.db")
