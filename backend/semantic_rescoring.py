import sqlite3
import random

def rescore():
    db_path = 'books.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # データの取得
    cursor.execute("SELECT id, title, author, plain_score, renown_score FROM books")
    rows = cursor.fetchall()
    
    # キーワードリスト
    style_hard_keywords = ['論', '考', '哲学', '思想', '研究', '史', '辞典', '議事録', '白書']
    style_soft_keywords = ['！', '？', 'ちゃん', '異世界', '転生', '令嬢', 'チート', '無双', '幼馴染']
    renown_mass_authors = ['夏目漱石', '芥川龍之介', '太宰治', '宮沢賢治', '森鴎外', '江戸川乱歩', '福沢諭吉', '紫式部', 'シェイクスピア']
    renown_niche_keywords = ['議事録', '会報', '草稿', '覚書', '報告書', '拾遺', '全集']
    
    print(f"Rescoring {len(rows)} records...")
    
    update_data = []
    for row in rows:
        book_id, title, author, style, renown = row
        title = title or ""
        author = author or ""
        
        style_delta = 0.0
        renown_delta = 0.0
        
        # Style 硬化 (+0.3)
        if any(k in title for k in style_hard_keywords) or any(k in author for k in style_hard_keywords):
            style_delta += 0.3
            
        # Style 軟化 (-0.3)
        if any(k in title for k in style_soft_keywords) or any(k in author for k in style_soft_keywords) or len(title) >= 30:
            style_delta -= 0.3
            
        # Renown マス化 (+0.4)
        if any(a in author for a in renown_mass_authors):
            renown_delta += 0.4
            
        # Renown ニッチ化 (-0.4)
        if any(k in title for k in renown_niche_keywords):
            renown_delta -= 0.4
            
        # 新スコア計算 (揺らぎ付与)
        new_style = style + style_delta + random.uniform(-0.05, 0.05)
        new_renown = renown + renown_delta + random.uniform(-0.05, 0.05)
        
        # クランプ (0.0 - 1.0)
        new_style = max(0.0, min(1.0, new_style))
        new_renown = max(0.0, min(1.0, new_renown))
        
        update_data.append((new_style, new_renown, book_id))
    
    # 一括アップデート
    cursor.executemany("UPDATE books SET plain_score = ?, renown_score = ? WHERE id = ?", update_data)
    conn.commit()
    
    print(f"Update complete. {len(update_data)} records modified.")
    conn.close()

if __name__ == "__main__":
    rescore()
