import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

def visualize():
    db_path = 'books.db'
    conn = sqlite3.connect(db_path)
    
    print("--- Distribution Analysis Start ---")
    query = "SELECT plain_score, renown_score FROM books"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"Total records fetched: {len(df)}")
    
    # 欠損値があれば補完 (0.0 とする)
    df['plain_score'] = df['plain_score'].fillna(0.0)
    df['renown_score'] = df['renown_score'].fillna(0.0)
    
    # 可視化設定 (2D ヒストグラム)
    plt.figure(figsize=(10, 8), facecolor='#121212')
    ax = plt.gca()
    ax.set_facecolor('#121212')
    
    # 背景に「団子状態」が浮き出るようなカラーマップを使用
    hb = plt.hist2d(
        df['renown_score'], 
        df['plain_score'], 
        bins=50, 
        cmap='magma',
        cmin=1
    )
    
    cb = plt.colorbar(hb[3], ax=ax)
    cb.set_label('Density (Book Count)', color='white')
    cb.ax.yaxis.set_tick_params(color='white')
    plt.setp(plt.getp(cb.ax.axes, 'yticklabels'), color='white')
    
    # ラベル設定
    plt.title('Lemma Book Space: Before Distribution', color='white', pad=20, fontsize=16)
    plt.xlabel('Renown / 知名度 (0.0: Niche, 1.0: Mass)', color='gray')
    plt.ylabel('Style / 文体 (0.0: Plain, 1.0: Hard)', color='gray')
    
    plt.tick_params(labelcolor='white', color='gray')
    
    # 保存
    output_path = 'distribution_before.png'
    plt.savefig(output_path, facecolor='#121212', bbox_inches='tight')
    plt.close()
    
    print(f"Visualization saved to: {output_path}")

if __name__ == "__main__":
    visualize()
