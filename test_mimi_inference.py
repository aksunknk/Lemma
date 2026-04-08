import requests
import json

def test_mimi_extraction(prompt_text):
    url = "http://localhost:11434/api/generate"
    system_prompt = "入力文を解析し、年代・国内外・文体・知名度を0.0から1.0で評価した4つの数値からなるJSON配列のみを出力せよ（不明な次元は0.5とし、配列以外のいかなる文字列の出力も禁止する）。"
    
    payload = {
        "model": "qwen2.5:7b",
        "prompt": f"{system_prompt}\n\n入力: {prompt_text}",
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json().get("response", "").strip()
        print(f"抽出ベクトル: {result}")
    except Exception as e:
        print(f"通信エラー: {e}")

if __name__ == "__main__":
    test_mimi_extraction("最近疲れているので、頭を使わずに笑える軽い本が読みたい")