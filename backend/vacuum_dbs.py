import sqlite3
import os

DB_FILES = [
    "lemma_master.db",
    "lemma_new_books.db",
    "lemma_manga.db"
]

def vacuum_dbs():
    for db_file in DB_FILES:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_file)
        if os.path.exists(path):
            print(f"Vacuuming {db_file}...")
            try:
                conn = sqlite3.connect(path)
                conn.execute("VACUUM;")
                conn.close()
                print(f"Successfully vacuumed {db_file}.")
            except Exception as e:
                print(f"Failed to vacuum {db_file}: {e}")
        else:
            print(f"File not found: {db_file}")

if __name__ == "__main__":
    vacuum_dbs()
