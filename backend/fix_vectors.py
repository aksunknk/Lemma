import sqlite3
import pandas as pd

def diagnose_era_errors(db_path="lemma_master.db"):
    conn = sqlite3.connect(db_path)
    
    print(f"[{db_path}] 空間の時間の歪み（ERAベクトルの異常値）をスキャン中...\n")
    df = pd.read_sql_query("SELECT isbn, title, author, era FROM books", conn)
    
    # ターゲット1: 正規化漏れ（値が1.0を大きく超えている、生の西暦などのデータ）
    # ※多少のオーバーシュートを許容し、2.0以上を明らかな異常値とする
    raw_year_errors = df[df['era'] > 2.0]
    
    # ターゲット2: 完全な 0.0 （発行年不明によるデフォルト値の吹きだまりの疑い）
    zero_era_errors = df[df['era'] == 0.0]
    
    print("="*50)
    print(f"[異常検知 A] 正規化漏れ（生の数値・2.0超過） : {len(raw_year_errors):,} 件")
    print(f"[異常検知 B] 年代が完全な 0.0（欠損値の疑い） : {len(zero_era_errors):,} 件")
    print("="*50)
    
    if not raw_year_errors.empty:
        print("\n■ サンプル: 正規化漏れの疑い（era > 2.0）")
        print(raw_year_errors[['title', 'author', 'era']].sample(n=min(3, len(raw_year_errors))).to_string(index=False))
        
    if not zero_era_errors.empty:
        print("\n■ サンプル: 年代が完全な 0.0 のデータ")
        print(zero_era_errors[['title', 'author', 'era']].sample(n=min(3, len(zero_era_errors))).to_string(index=False))

    conn.close()

if __name__ == "__main__":
    diagnose_era_errors()