import sqlite3

def clean_database():
    db_path = 'books.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 削除前の件数確認
        cursor.execute("SELECT COUNT(*) FROM books")
        total_before = cursor.fetchone()[0]

        # 不純物データの削除 (author が UNKNOWN, NULL, または空文字)
        query = """
            DELETE FROM books 
            WHERE author IS NULL 
               OR author = '' 
               OR author = 'UNKNOWN'
        """
        cursor.execute(query)
        deleted_count = cursor.rowcount
        
        conn.commit()

        # 削除後の件数確認
        cursor.execute("SELECT COUNT(*) FROM books")
        total_after = cursor.fetchone()[0]

        print(f"--- Database Cleanup Report ---")
        print(f"Deleted: {deleted_count} records")
        print(f"Total before: {total_before}")
        print(f"Total after: {total_after}")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clean_database()
