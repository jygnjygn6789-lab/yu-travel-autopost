"""
一鍵取得 Facebook 粉專 Page Access Token
執行後會自動開啟瀏覽器讓你授權，完成後自動寫入 .env
"""
import os
import sys
import json
import webbrowser
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv, set_key

load_dotenv(".env", override=True)

APP_ID = os.getenv("FB_APP_ID", "857804396816755")
APP_SECRET = os.getenv("FB_APP_SECRET", "")
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1191144084074179")
REDIRECT_URI = "http://localhost:5001/callback"
SCOPE = "pages_manage_posts,pages_read_engagement,pages_show_list,instagram_content_publish"

# 儲存授權碼用
auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            auth_code = params["code"][0]
            body = b"<html><body style='font-family:sans-serif;text-align:center;padding:60px'><h2>OK! Token getting...</h2><p>This window can be closed.</p></body></html>"
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
        elif "error" in params:
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            error = params.get("error_description", ["未知錯誤"])[0]
            self.wfile.write(f"<h2>❌ 授權失敗: {error}</h2>".encode("utf-8"))
        else:
            self.send_response(200)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # 不印 log


def exchange_code_for_token(code):
    """用授權碼換取短效 User Access Token"""
    resp = requests.get("https://graph.facebook.com/v21.0/oauth/access_token", params={
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    })
    return resp.json()


def get_long_lived_token(short_token):
    """把短效 token 換成 60 天長效 token"""
    resp = requests.get("https://graph.facebook.com/v21.0/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": short_token,
    })
    return resp.json()


def get_page_token(user_token):
    """用 User Token 取得粉專的 Page Access Token"""
    resp = requests.get("https://graph.facebook.com/v21.0/me/accounts", params={
        "access_token": user_token,
    })
    data = resp.json()
    if "data" not in data:
        return None, data

    for page in data["data"]:
        if page.get("id") == FB_PAGE_ID:
            return page["access_token"], page
        # 也印出所有找到的粉專，方便確認
    print(f"找到的粉專: {[p.get('name') for p in data['data']]}")
    # 若只有一個粉專直接回傳
    if len(data["data"]) == 1:
        return data["data"][0]["access_token"], data["data"][0]
    return None, data


def save_token_to_env(token):
    """把 token 寫進 .env"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "FB_PAGE_TOKEN=" in content:
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("FB_PAGE_TOKEN="):
                new_lines.append(f"FB_PAGE_TOKEN={token}")
            else:
                new_lines.append(line)
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
    else:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\nFB_PAGE_TOKEN={token}\n")


if __name__ == "__main__":
    # 1. 開啟 FB 授權頁面
    auth_url = (
        f"https://www.facebook.com/dialog/oauth"
        f"?client_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPE}"
        f"&response_type=code"
    )
    # 1. 先啟動本機 callback 伺服器
    server = HTTPServer(("localhost", 5001), CallbackHandler)
    server.timeout = 120

    # 2. 再開瀏覽器
    print("正在開啟 Facebook 授權頁面...")
    print(f"若瀏覽器沒有自動開啟，請手動前往：\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("等待授權完成（請在瀏覽器中登入並允許）...")
    while auth_code is None:
        server.handle_request()

    print(f"\n授權碼取得成功，正在換取 Token...")

    # 3. 換取短效 User Token
    token_data = exchange_code_for_token(auth_code)
    if "access_token" not in token_data:
        print(f"換取 Token 失敗: {token_data}")
        sys.exit(1)

    short_token = token_data["access_token"]
    print("短效 User Token 取得成功")

    # 4. 換成長效 Token（60 天）
    long_data = get_long_lived_token(short_token)
    if "access_token" not in long_data:
        print(f"換取長效 Token 失敗: {long_data}")
        user_token = short_token
    else:
        user_token = long_data["access_token"]
        print(f"長效 User Token 取得成功（有效期：{long_data.get('expires_in', '?')} 秒）")

    # 5. 取得 Page Access Token
    print("正在取得粉專 Page Access Token...")
    page_token, page_info = get_page_token(user_token)

    if not page_token:
        print(f"取得 Page Token 失敗: {page_info}")
        sys.exit(1)

    page_name = page_info.get("name", "未知粉專") if isinstance(page_info, dict) else "?"
    print(f"\n[OK] Page Access Token for [{page_name}] obtained!")
    print(f"Token: {page_token[:30]}...")

    # 6. 寫入 .env
    save_token_to_env(page_token)
    print("\n[OK] FB_PAGE_TOKEN saved to .env")
    print("FB page auto-post is ready!")
