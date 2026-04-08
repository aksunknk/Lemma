import subprocess
import time
import re
import os
import sys

def start_system():
    print("Starting Lemma Search Engine (1.2M Records Mode)...")
    
    # 1. FastAPI サーバーの起動
    # reload=True は開発用
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # 2. Cloudflare Tunnel の起動
    tunnel_cmd = [
        "cloudflared.exe", "tunnel", "--url", "http://localhost:8000"
    ]
    
    tunnel_proc = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    public_url = None
    print("Waiting for Quick Tunnel URL...")
    
    try:
        while True:
            line = tunnel_proc.stdout.readline()
            if not line:
                break
            
            # URLの抽出
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match:
                public_url = match.group(0)
                print("\n" + "="*50)
                print(f"PUBLIC URL: {public_url}")
                print("="*50 + "\n")
                
                # URLをファイルに保存（FrontendやTestで使用）
                with open("current_url.txt", "w") as f:
                    f.write(public_url)
                break
                
            if "error" in line.lower():
                print(f"Tunnel Log: {line.strip()}")
                
        print("Server is running. Press Ctrl+C to stop.")
        
        # ログの監視（必要に応じて）
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_proc.terminate()
        tunnel_proc.terminate()

if __name__ == "__main__":
    start_system()
