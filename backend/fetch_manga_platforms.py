import asyncio
import random
import re
import sqlite3
import time
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm

DB_PATH = "lemma_manga.db"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

PLATFORM_CONFIG = {
    "少年ジャンプ＋": {"style": 0.3, "renown": 0.8},
    "裏サンデー": {"style": 0.6, "renown": 0.7},
    "マガジンポケット": {"style": 0.4, "renown": 0.75},
}

async def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS manga (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            source TEXT,
            era REAL,
            origin REAL,
            style REAL,
            renown REAL,
            UNIQUE(title, author, source)
        )
    """)
    conn.commit()
    return conn

async def save_manga(conn, title, author, source):
    cursor = conn.cursor()
    era = 0.95 
    origin = 0.0
    style, renown = PLATFORM_CONFIG.get(source, {"style": 0.5, "renown": 0.5}).values()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO manga (title, author, source, era, origin, style, renown)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, author, source, era, origin, style, renown))
        conn.commit()
        return 1 if cursor.rowcount > 0 else 0
    except:
        return 0

async def fetch_ura_sunday(page, conn):
    print("Scraping Ura Sunday (MangaOne)...")
    await page.goto("https://manga-one.com/titles/rensai", wait_until="networkidle")
    
    # 曜日タブの取得（最新修正: クラス指定）
    tab_buttons = await page.query_selector_all("button.flex.grow.items-center.justify-center")
    
    all_targets = {}
    for i in range(len(tab_buttons)):
        try:
            # タブをクリック
            current_tabs = await page.query_selector_all("button.flex.grow.items-center.justify-center")
            await current_tabs[i].click()
            await asyncio.sleep(3) # コンテンツ読み込み待機
            
            links = await page.query_selector_all("a:has(h4)")
            for link in links:
                title_el = await link.query_selector("h4")
                href = await link.get_attribute("href")
                if title_el and href:
                    title = (await title_el.inner_text()).strip()
                    match = re.search(r"/manga/(\d+)", href)
                    if match:
                        manga_id = match.group(1)
                        all_targets[title] = f"https://manga-one.com/title/{manga_id}"
        except Exception as e:
            print(f"Tab click error at index {i}: {e}")

    targets = [{"title": t, "url": u} for t, u in all_targets.items()]
    random.shuffle(targets)
    
    new_count = 0
    for target in tqdm(targets[:80], desc="Ura Sunday (Stealth Details)"):
        try:
            detail_page = await page.context.new_page()
            await asyncio.sleep(random.uniform(12.0, 25.0)) # 徹底待機
            
            await detail_page.goto(target["url"], wait_until="domcontentloaded")
            # 最新セレクタ: #aboutTitle p.text-[13px]
            author = "Unknown"
            author_el = await detail_page.query_selector("#aboutTitle p.text-\\[13px\\]")
            if not author_el:
                author_el = await detail_page.query_selector("section#aboutTitle div.bg-\\[\\#FBFBFB\\] p")
            
            if author_el:
                raw_text = await author_el.inner_text()
                author = raw_text.replace("著者：", "").replace("著者", "").strip()
                
            new_count += await save_manga(conn, target["title"], author, "裏サンデー")
            await detail_page.close()
            
            if (new_count % 5) == 0: await asyncio.sleep(30)
        except Exception as e:
            print(f"Error at {target['title']}: {e}")
            
    return new_count

async def fetch_magapoke(page, conn):
    print("Scraping Magazine Pocket...")
    await page.goto("https://pocket.shonenmagazine.com/series", wait_until="networkidle")
    
    # 曜日ごとのセクション
    await page.wait_for_selector(".c-series-item")
    
    items = await page.query_selector_all(".c-series-item")
    new_count = 0
    for item in tqdm(items, desc="Magapoke"):
        try:
            # 最新セレクタ: h3
            title_el = await item.query_selector("h3")
            # 著者は h4 または p にある可能性
            author_el = await item.query_selector(".c-series-item__author")
            if not author_el:
                author_el = await item.query_selector("p, h4") # フォールバック
                
            if title_el and author_el:
                title = (await title_el.inner_text()).strip()
                author = (await author_el.inner_text()).strip()
                new_count += await save_manga(conn, title, author, "マガジンポケット")
        except: continue
    return new_count

async def main():
    conn = await init_db()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        try:
            u_count = await fetch_ura_sunday(page, conn)
            print(f"Ura Sunday Total: {u_count}")
            
            m_count = await fetch_magapoke(page, conn)
            print(f"Magapoke Total: {m_count}")
        except Exception as e:
            print(f"Fatal: {e}")
        finally:
            await browser.close()
            conn.close()

if __name__ == "__main__":
    asyncio.run(main())
