import subprocess
import time
import re
import os
import sys
import requests

# 絶対パスの設定
BASE_DIR = r"C:\Users\aksak\lemma_project_core\backend"
PYTHON_EXE = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
CLOUDFLARED_EXE = os.path.join(BASE_DIR, "cloudflared.exe")
URL_FILE = os.path.join(BASE_DIR, "current_url.txt")

def start_system():
    # 既存プロセスの掃除
    print("Cleaning up existing processes...")
    subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe", "/T"], capture_output=True)
    time.sleep(2)

    print(f"Starting Backend (FastAPI) from {BASE_DIR}...")
    # バックエンドの起動 (ログをファイルへ)
    with open(os.path.join(BASE_DIR, "backend.log"), "w") as f_log:
        backend_proc = subprocess.Popen(
            [PYTHON_EXE, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=f_log,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR
        )

    # 1.2M レコードのロード待機 (Health Check)
    print("Waiting for API to be ready (Loading 1.2M records... Timeout: 240s)...")
    max_retries = 240 # 240秒待機
    api_ready = False
    for i in range(max_retries):
        try:
            # api/search ではなく、FastAPIの起動を確認するためルートまたは docs などを叩くのも手だが、
            # 完璧な「準備完了」を確認するため、あえて空検索を試行。
            resp = requests.post("http://localhost:8000/api/search", json={"query": ""}, timeout=2)
            if resp.status_code in [200, 404]: # 404もエンジンが応答している証拠
                api_ready = True
                print("API is READY.")
                break
        except:
            if i % 5 == 0:
                print(f"Still loading... ({i}s)")
            time.sleep(1)
    
    if not api_ready:
        print("API failed to start in time. Check backend.log.")
        backend_proc.terminate()
        return

    # 2. Cloudflare Tunnel の起動
    print("Starting Cloudflare Quick Tunnel...")
    with open(os.path.join(BASE_DIR, "tunnel.log"), "w") as f_tunnel:
        tunnel_proc = subprocess.Popen(
            [CLOUDFLARED_EXE, "tunnel", "run", "lemma-tunnel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=BASE_DIR
        )

    public_url = None
    print("Extracting Quick Tunnel URL...")
    
    try:
        # Tunnel ログから URL を抽出
        while True:
            line = tunnel_proc.stdout.readline()
            if not line: break
            
            # 補助的に tunnel.log にも書き出す
            with open(os.path.join(BASE_DIR, "tunnel.log"), "a") as f_t:
                f_t.write(line)

            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match:
                public_url = match.group(0)
                print("\n" + "="*60)
                print(f"STABLE PUBLIC URL: {public_url}")
                print("="*60 + "\n")
                
                with open(URL_FILE, "w") as f:
                    f.write(public_url)
                break

        print("Press Ctrl+C to shutdown both backend and tunnel.")
        while True:
            time.sleep(5)
            # 生存確認
            if backend_proc.poll() is not None:
                print("Backend process died unexpectedly.")
                break
            if tunnel_proc.poll() is not None:
                print("Tunnel process died unexpectedly.")
                break

    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_proc.terminate()
        tunnel_proc.terminate()

if __name__ == "__main__":
    start_system()
