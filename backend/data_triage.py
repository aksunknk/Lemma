import sqlite3
import pandas as pd

def run_diagnostics_v2(db_path="lemma_master.db", table_name="books"):
    conn = sqlite3.connect(db_path)
    
    print(f"[{db_path}] を高解像度スキャン中...")
    df = pd.read_sql_query(f"SELECT isbn, title, author FROM {table_name}", conn)
    total_records = len(df)
    
    # ルールA: 商業的ノイズ（宣伝用ブラケット等）の混入
    promo_authors = df[df['author'].fillna('').str.contains(r'【|】|★|☆|◆|◇', regex=True)]
    
    # ルールB: 異常な長さ（50文字以上。複数の共著者を考慮しても長すぎる完全なゴミデータ）
    extreme_authors = df[df['author'].fillna('').str.len() > 50]
    
    # ルールC: タイトルと著者名が完全に同一（あなたが危惧していた「2008」のような謎データの正体）
    # ※空欄同士の一致を避けるため、文字数1以上のものに限定
    duplicate_noise = df[(df['title'] == df['author']) & (df['title'].str.len() > 0)]
    
    print("="*50)
    print(f"総レコード数: {total_records:,} 件")
    print("-" * 50)
    print(f"[異常検知 A] 宣伝記号(【】★等)を含む著者 : {len(promo_authors):,} 件")
    print(f"[異常検知 B] 著者名が50文字超過         : {len(extreme_authors):,} 件")
    print(f"[異常検知 C] タイトルと著者が完全一致     : {len(duplicate_noise):,} 件")
    print("="*50)
    
    if not promo_authors.empty:
        print("\n■ サンプル: 宣伝記号が混入した著者")
        print(promo_authors[['title', 'author']].head(3).to_string(index=False))
        
    if not duplicate_noise.empty:
        print("\n■ サンプル: タイトルと著者が完全一致する異常データ")
        print(duplicate_noise[['title', 'author']].head(3).to_string(index=False))

    conn.close()

if __name__ == "__main__":
    run_diagnostics_v2("lemma_master.db", "books")