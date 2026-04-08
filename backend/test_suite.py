import asyncio
import httpx
import os
import json
from typing import List, Dict, Any

async def run_test(client: httpx.AsyncClient, base_url: str, query: str) -> Dict[str, Any]:
    # URL 末尾のスラッシュやエンコーディングの問題を解決
    url = f"{base_url.strip().strip('').rstrip('/')}/api/search"
    payload = {"query": query}
    try:
        response = await client.post(url, json=payload, timeout=20.0)
        try:
            data = response.json()
        except:
            data = {"detail": response.text}
        
        return {
            "query": query,
            "status": response.status_code,
            "data": data,
            "success": response.status_code in [200, 404]
        }
    except Exception as e:
        return {
            "query": query,
            "status": "ERROR",
            "data": {"detail": str(e)},
            "success": False
        }

def summarize_response(status: Any, data: Any) -> str:
    if not isinstance(data, dict):
        return f"RAW: {str(data)[:50]}"
        
    if status == 200:
        title = data.get("title", "Unknown")
        cat = data.get("category", "-")
        dist = data.get("distance", 0.0)
        vec = data.get("vector", [])
        vec_str = ",".join([f"{v:.1f}" for v in vec])
        return f"OK: {title} ({cat}) [V:{vec_str}] (d={dist:.2f})"
    elif status == 404:
        msg = data.get("detail", data.get("message", "Not Found"))
        return f"404: {msg}"
    elif status == 422:
        return f"422: Validation Error"
    else:
        msg = data.get("detail", "Unknown Error")
        return f"ERR({status}): {msg}"

async def main():
    # URLの読み込み (エンコーディングに対して寛容に)
    if not os.path.exists("current_url.txt"):
        print("Error: current_url.txt not found.")
        return

    base_url = ""
    # PowerShellの echo が UTF-16 を吐くことがあるため複数を試行
    for enc in ['utf-8-sig', 'utf-16', 'utf-8', 'latin-1']:
        try:
            with open("current_url.txt", "r", encoding=enc) as f:
                base_url = f.read().strip()
            if base_url: break
        except:
            continue

    if not base_url:
        print("Error: Could not read valid URL from current_url.txt.")
        return

    test_cases = [
        "哲学的なSF漫画、少し古め",
        "心が温まる、知名度のある活字本",
        "古典的な海外の小説",
        "",
        " ",
        "SF",
        "非常に長いクエリ" * 10,
        "🎨🎌📚",
        "今日の東京の天気",
        "活字本を読みたい",
        "マンガを探している",
        "2030"
    ]

    print(f"# Testing lemma_core at {base_url}")
    print("| Query | Status | Response Summary | Success |")
    print("| :--- | :--- | :--- | :--- |")

    async with httpx.AsyncClient() as client:
        tasks = [run_test(client, base_url, q) for q in test_cases ]
        results = await asyncio.gather(*tasks)

        for res in results:
            summary = summarize_response(res["status"], res["data"])
            status_str = str(res["status"])
            success_emoji = "✅" if res["success"] else "❌"
            print(f"| {res['query']} | {status_str} | {summary} | {success_emoji} |")

if __name__ == "__main__":
    asyncio.run(main())
