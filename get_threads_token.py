# -*- coding: utf-8 -*-
"""
一鍵取得 Threads Access Token
執行後自動開啟瀏覽器授權，完成後自動寫入 .env

前置條件：
  1. 到 https://developers.facebook.com/apps/857804396816755/
  2. 左側「新增產品」→ 加入「Threads API」
  3. Threads API 設定 → 在「使用者 Token 產生器」加入你的帳號為測試用戶
  4. 確認 redirect_uri http://localhost:5001/callback 已在 Threads API 設定中加入
"""
import os, sys, webbrowser, requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv(".env", override=True)

APP_ID       = os.getenv("FB_APP_ID", "857804396816755")
APP_SECRET   = os.getenv("FB_APP_SECRET", "b55ab214bcaf99b9563686ff660b7942")
REDIRECT_URI = "http://localhost:5001/callback"
SCOPE        = "threads_basic,threads_content_publish"

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            body = b"<html><body style='font-family:sans-serif;text-align:center;padding:60px'><h2>Threads 授權成功！可以關閉此視窗</h2></body></html>"
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif "error" in params:
            err = params.get("error_description", ["未知錯誤"])[0]
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h2>授權失敗: {err}</h2>".encode())
        else:
            self.send_response(200); self.end_headers()

    def log_message(self, *args): pass


def exchange_code(code: str) -> dict:
    """授權碼換短效 Token"""
    r = requests.post(
        "https://graph.threads.net/oauth/access_token",
        data={
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
        timeout=15,
    )
    return r.json()


def get_long_lived_token(short_token: str) -> dict:
    """短效換長效 Token（60 天）"""
    r = requests.get(
        "https://graph.threads.net/access_token",
        params={
            "grant_type": "th_exchange_token",
            "client_secret": APP_SECRET,
            "access_token": short_token,
        },
        timeout=15,
    )
    return r.json()


def get_user_id(token: str) -> str | None:
    """取得 Threads 用戶 ID"""
    r = requests.get(
        "https://graph.threads.net/v1.0/me",
        params={"fields": "id,username", "access_token": token},
        timeout=15,
    )
    data = r.json()
    print(f"用戶資訊: {data}")
    return data.get("id"), data.get("username")


def save_to_env(key: str, value: str):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
    if f"{key}=" in content:
        lines = [f"{key}={value}" if l.startswith(f"{key}=") else l for l in content.splitlines()]
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    else:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\n{key}={value}\n")
    print(f"[OK] {key} 已寫入 .env")


if __name__ == "__main__":
    auth_url = (
        f"https://www.threads.net/oauth/authorize"
        f"?client_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPE}"
        f"&response_type=code"
    )

    server = HTTPServer(("localhost", 5001), CallbackHandler)
    server.timeout = 120

    print("正在開啟 Threads 授權頁面...")
    print(f"若未自動開啟，請手動前往：\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("等待授權完成...")
    while auth_code is None:
        server.handle_request()

    print(f"\n授權碼取得，換取 Token...")
    short_data = exchange_code(auth_code)
    if "access_token" not in short_data:
        print(f"換取 Token 失敗: {short_data}")
        sys.exit(1)

    short_token = short_data["access_token"]
    print("短效 Token 取得成功，換取長效 Token...")

    long_data = get_long_lived_token(short_token)
    if "access_token" not in long_data:
        print(f"長效 Token 失敗，使用短效: {long_data}")
        token = short_token
    else:
        token = long_data["access_token"]
        print(f"長效 Token 取得成功（有效期：{long_data.get('expires_in', '?')} 秒 ≈ 60 天）")

    user_id, username = get_user_id(token)
    if not user_id:
        print("無法取得用戶 ID，請確認帳號有開通 Threads")
        sys.exit(1)

    print(f"\n[OK] Threads 帳號：@{username}（ID: {user_id}）")

    save_to_env("THREADS_ACCESS_TOKEN", token)
    save_to_env("THREADS_USER_ID", user_id)

    print("\nThreads 自動發文設定完成！執行 python threads_poster.py 測試看看")
