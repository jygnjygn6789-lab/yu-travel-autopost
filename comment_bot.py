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

# WycBotAI 帳號（FB_PAGE_TOKEN + graph.facebook.com）
WYCBOTAI_IG_USER_ID = os.getenv("WYCBOTAI_IG_USER_ID")
FB_BASE_URL = "https://graph.facebook.com/v21.0"
WYC_DM_REPLIED_FILE = os.path.join(os.path.dirname(__file__), "wyc_dm_replied.json")

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
    """回覆留言（公開）"""
    token = os.getenv("IG_ACCESS_TOKEN")
    resp = requests.post(
        f"{BASE_URL}/{comment_id}/replies",
        data={"message": message, "access_token": token},
        timeout=15,
    )
    return resp.json()


def private_reply(comment_id: str, message: str) -> dict:
    """私訊回覆留言（需要 instagram_business_manage_messages 權限）"""
    token = os.getenv("IG_ACCESS_TOKEN")
    resp = requests.post(
        f"{BASE_URL}/{comment_id}/private_replies",
        data={"message": message, "access_token": token},
        timeout=15,
    )
    return resp.json()


# ── 關鍵字觸發設定 ─────────────────────────────────────────────────────────────
# 格式：{"keyword": "EMA", "dm_message": "...", "public_reply": "..."}
KEYWORD_TRIGGERS_FILE = os.path.join(os.path.dirname(__file__), "keyword_triggers.json")
DM_REPLIED_FILE = os.path.join(os.path.dirname(__file__), "dm_replied_comments.json")


def load_keyword_triggers() -> list:
    if os.path.exists(KEYWORD_TRIGGERS_FILE):
        with open(KEYWORD_TRIGGERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _load_dm_replied() -> set:
    if os.path.exists(DM_REPLIED_FILE):
        with open(DM_REPLIED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def _save_dm_replied(replied: set):
    with open(DM_REPLIED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(replied), f)


def run_keyword_dm_bot():
    """
    掃描最近貼文留言，發現關鍵字就自動私訊對方網址
    關鍵字設定在 keyword_triggers.json
    """
    triggers = load_keyword_triggers()
    if not triggers:
        print("[關鍵字DM] 無觸發設定，跳過")
        return

    dm_replied = _load_dm_replied()
    total_dm = 0

    posts = get_recent_posts(limit=10)
    if not posts:
        print("[關鍵字DM] 無法取得貼文，跳過")
        return

    for post in posts:
        media_id = post["id"]
        comments = get_comments(media_id)

        for comment in comments:
            comment_id = comment["id"]
            if comment_id in dm_replied:
                continue

            text    = comment.get("text", "").strip()
            username = comment.get("username", "")

            for trigger in triggers:
                keyword = trigger.get("keyword", "").strip()
                if not keyword:
                    continue
                # 不分大小寫、允許前後有其他文字
                if keyword.upper() in text.upper():
                    dm_msg     = trigger.get("dm_message", "")
                    pub_reply  = trigger.get("public_reply", "")

                    print(f"[關鍵字DM] @{username} 留言含「{keyword}」，發送 DM...")

                    # 私訊
                    if dm_msg:
                        result = private_reply(comment_id, dm_msg)
                        if "id" in result:
                            print(f"[關鍵字DM] DM 發送成功")
                            total_dm += 1
                        else:
                            print(f"[關鍵字DM] DM 失敗: {result}")

                    # 公開回覆（可選）
                    if pub_reply:
                        reply_to_comment(comment_id, pub_reply)

                    dm_replied.add(comment_id)
                    time.sleep(2)
                    break  # 一則留言只觸發一次

    _save_dm_replied(dm_replied)
    print(f"[關鍵字DM] 完成，共發送 {total_dm} 則 DM")


# ── WycBotAI 專用 DM Bot（FB_PAGE_TOKEN + graph.facebook.com）─────────────────

def _wyc_get_recent_posts(limit=10) -> list:
    token = os.getenv("FB_PAGE_TOKEN")
    resp = requests.get(
        f"{FB_BASE_URL}/{WYCBOTAI_IG_USER_ID}/media",
        params={"fields": "id,caption,timestamp", "limit": limit, "access_token": token},
        timeout=15,
    )
    return resp.json().get("data", [])


def _wyc_get_comments(media_id: str) -> list:
    token = os.getenv("FB_PAGE_TOKEN")
    resp = requests.get(
        f"{FB_BASE_URL}/{media_id}/comments",
        params={"fields": "id,text,username,timestamp", "access_token": token},
        timeout=15,
    )
    return resp.json().get("data", [])


def _wyc_private_reply(comment_id: str, message: str) -> dict:
    token = os.getenv("FB_PAGE_TOKEN")
    resp = requests.post(
        f"{FB_BASE_URL}/me/messages",
        params={"access_token": token},
        json={
            "recipient": {"comment_id": comment_id},
            "message": {"text": message},
        },
        timeout=15,
    )
    return resp.json()


def _load_wyc_dm_replied() -> set:
    if os.path.exists(WYC_DM_REPLIED_FILE):
        with open(WYC_DM_REPLIED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def _save_wyc_dm_replied(replied: set):
    with open(WYC_DM_REPLIED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(replied), f)


def run_wycbotai_keyword_dm():
    """
    WycBotAI 帳號：掃描最近貼文留言，偵測關鍵字後自動私訊 DC 連結
    使用 FB_PAGE_TOKEN + graph.facebook.com
    """
    triggers = load_keyword_triggers()
    if not triggers:
        print("[WycDM] 無觸發設定，跳過")
        return

    replied = _load_wyc_dm_replied()
    total_dm = 0

    posts = _wyc_get_recent_posts(limit=10)
    if not posts:
        print("[WycDM] 無法取得貼文，跳過")
        return

    for post in posts:
        media_id = post["id"]
        comments = _wyc_get_comments(media_id)

        for comment in comments:
            comment_id = comment["id"]
            if comment_id in replied:
                continue

            text     = comment.get("text", "").strip()
            username = comment.get("username", "")

            for trigger in triggers:
                keyword = trigger.get("keyword", "").strip()
                if not keyword:
                    continue
                if keyword.upper() in text.upper():
                    dm_msg    = trigger.get("dm_message", "")
                    pub_reply = trigger.get("public_reply", "")

                    print(f"[WycDM] @{username} 留言含「{keyword}」，發送 DC 連結...")

                    if dm_msg:
                        result = _wyc_private_reply(comment_id, dm_msg)
                        if "id" in result:
                            print(f"[WycDM] DM 發送成功 → @{username}")
                            total_dm += 1
                        else:
                            print(f"[WycDM] DM 失敗: {result}")

                    if pub_reply:
                        token = os.getenv("FB_PAGE_TOKEN")
                        pr = requests.post(
                            f"{FB_BASE_URL}/{comment_id}/replies",
                            data={"message": pub_reply, "access_token": token},
                            timeout=15,
                        ).json()
                        if "id" in pr:
                            print(f"[WycDM] 公開回覆成功 → @{username}")
                        else:
                            print(f"[WycDM] 公開回覆失敗: {pr}")

                    replied.add(comment_id)
                    time.sleep(2)
                    break

    _save_wyc_dm_replied(replied)
    print(f"[WycDM] 完成，共發送 {total_dm} 則 DM")


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
