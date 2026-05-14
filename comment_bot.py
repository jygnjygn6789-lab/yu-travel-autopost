"""
IG 留言自動按讚 + 回覆模組
每 30 分鐘掃描最近貼文的新留言，自動按讚並用 Claude 生成回覆
"""
import os
import json
import time
import requests
from dotenv import load_dotenv
import anthropic

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

IG_USER_ID = os.getenv("IG_USER_ID")
BASE_URL = "https://graph.instagram.com/v21.0"

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 已處理留言的紀錄檔（避免重複回覆）
REPLIED_FILE = os.path.join(os.path.dirname(__file__), "replied_comments.json")


def _load_replied() -> set:
    if os.path.exists(REPLIED_FILE):
        with open(REPLIED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def _save_replied(replied: set):
    with open(REPLIED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(replied), f)


def get_recent_posts(limit=5) -> list:
    """取得最近貼文列表"""
    token = os.getenv("IG_ACCESS_TOKEN")
    resp = requests.get(
        f"{BASE_URL}/{IG_USER_ID}/media",
        params={"fields": "id,caption,timestamp", "limit": limit, "access_token": token},
        timeout=15,
    )
    return resp.json().get("data", [])


def get_comments(media_id: str) -> list:
    """取得某貼文的所有留言"""
    token = os.getenv("IG_ACCESS_TOKEN")
    resp = requests.get(
        f"{BASE_URL}/{media_id}/comments",
        params={"fields": "id,text,username,timestamp", "access_token": token},
        timeout=15,
    )
    return resp.json().get("data", [])


def like_comment(comment_id: str) -> bool:
    """按讚留言"""
    token = os.getenv("IG_ACCESS_TOKEN")
    resp = requests.post(
        f"{BASE_URL}/{comment_id}/likes",
        data={"access_token": token},
        timeout=15,
    )
    return resp.json().get("success", False)


def reply_to_comment(comment_id: str, message: str) -> dict:
    """回覆留言"""
    token = os.getenv("IG_ACCESS_TOKEN")
    resp = requests.post(
        f"{BASE_URL}/{comment_id}/replies",
        data={"message": message, "access_token": token},
        timeout=15,
    )
    return resp.json()


def generate_reply(username: str, comment_text: str, post_caption: str = "") -> str:
    """用 Claude Haiku 生成自然的留言回覆"""
    prompt = f"""你是台灣旅遊 IG 帳號「Yu的出國旅遊大全」的小編，個性親切活潑。

粉絲 @{username} 留言：「{comment_text}」

貼文主題：{post_caption[:80] if post_caption else "旅遊優惠特價"}

回覆規則：
- 20字以內，簡短自然
- 繁體中文，語氣像朋友聊天
- 如果問訂票/連結，說「連結在主頁！」
- 如果是讚美，簡單感謝
- 最多 1 個 emoji
- 直接輸出回覆，不要加任何說明"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=80,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def run_comment_bot():
    """主流程：掃描新留言 → 按讚 → 回覆"""
    print("\n[留言機器人] 開始掃描...")
    replied = _load_replied()
    total_liked = 0
    total_replied = 0

    posts = get_recent_posts(limit=5)
    if not posts:
        print("[留言機器人] 無法取得貼文，跳過")
        return

    for post in posts:
        media_id = post["id"]
        caption = post.get("caption", "")
        comments = get_comments(media_id)

        for comment in comments:
            comment_id = comment["id"]
            text = comment.get("text", "")
            username = comment.get("username", "")

            if comment_id in replied:
                continue

            print(f"[留言機器人] @{username}: {text[:40]}")

            # 按讚
            try:
                if like_comment(comment_id):
                    total_liked += 1
                    print(f"[留言機器人] 已按讚")
            except Exception as e:
                print(f"[留言機器人] 按讚失敗: {e}")

            # 生成並回覆
            try:
                reply_text = generate_reply(username, text, caption)
                result = reply_to_comment(comment_id, reply_text)
                if "id" in result:
                    total_replied += 1
                    print(f"[留言機器人] 回覆: {reply_text}")
                else:
                    print(f"[留言機器人] 回覆失敗: {result}")
            except Exception as e:
                print(f"[留言機器人] 回覆錯誤: {e}")

            replied.add(comment_id)
            time.sleep(2)  # 避免速率限制

    _save_replied(replied)
    print(f"[留言機器人] 完成 — 按讚 {total_liked} 則，回覆 {total_replied} 則")
