# -*- coding: utf-8 -*-
"""
Origin誤分類パッチ: 著者名が日本語主体の書籍を origin_domestic=True に修正する。
判定ロジック:
  - 著者名に中黒（・）やアルファベットが含まれる → 海外著者の可能性が高いため変更しない
  - 著者名が漢字・ひらがな・カタカナ主体 → 日本人著者として origin_domestic=True に修正
"""
import sqlite3
import re
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "books.db")

def is_japanese_author(name: str) -> bool:
    """著者名が日本人名かどうかを判定する。"""
    if not name or not name.strip():
        return False

    name = name.strip()

    # 中黒（・）を含む場合はカタカナ外国人名の可能性が高い（例: Ｆ・コプルストン）
    if "・" in name or "·" in name:
        return False

    # ASCII アルファベットを含む場合は海外著者
    if re.search(r'[A-Za-z]', name):
        return False

    # 全角アルファベットを含む場合も海外著者（例: Ｆ・コプルストン）
    if re.search(r'[Ａ-Ｚａ-ｚ]', name):
        return False

    # 漢字・ひらがな・カタカナが主体かチェック
    # CJK統合漢字 + ひらがな + カタカナ
    jp_chars = len(re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', name))
    total_chars = len(re.sub(r'\s', '', name))

    if total_chars == 0:
        return False

    # 日本語文字が全体の70%以上であれば日本人著者と判定
    return (jp_chars / total_chars) >= 0.7


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 現在 origin_domestic=0 (海外扱い) のレコードを取得
    cursor.execute("SELECT id, author, title FROM books WHERE origin_domestic = 0")
    foreign_books = cursor.fetchall()

    print(f"現在の海外扱い書籍数: {len(foreign_books)}")
    print("-" * 60)

    fixed_count = 0
    fixed_books = []

    for book_id, author, title in foreign_books:
        if is_japanese_author(author):
            cursor.execute(
                "UPDATE books SET origin_domestic = 1 WHERE id = ?",
                (book_id,)
            )
            fixed_count += 1
            fixed_books.append((author, title))

    conn.commit()

    print(f"\n修正された書籍数: {fixed_count}")
    print("-" * 60)
    for author, title in fixed_books:
        print(f"  [{author}] {title}")

    # 修正後の分布を表示
    cursor.execute("SELECT COUNT(*) FROM books WHERE origin_domestic = 1")
    domestic = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM books WHERE origin_domestic = 0")
    foreign = cursor.fetchone()[0]
    print(f"\n修正後の分布: 国内={domestic}, 海外={foreign}")

    conn.close()


if __name__ == "__main__":
    main()
