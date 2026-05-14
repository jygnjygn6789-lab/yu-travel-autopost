"""
Facebook Page 自動發文模組
需要在 .env 設定 FB_PAGE_TOKEN（粉專存取權杖）
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_API_BASE = "https://graph.facebook.com/v21.0"


def _get_page_token() -> str:
    """取得粉專 Access Token"""
    token = os.getenv("FB_PAGE_TOKEN")
    if not token:
        raise ValueError("請在 .env 設定 FB_PAGE_TOKEN（粉專存取權杖）")
    return token


def post_fb_feed(image_url: str, caption: str) -> dict:
    """
    發布 Facebook 粉專貼文（圖片 + 文字）
    image_url: 公開可訪問的圖片 URL
    caption: 貼文文字
    """
    token = _get_page_token()

    # Step 1: 上傳圖片（unpublished）
    photo_url = f"{FB_API_BASE}/{FB_PAGE_ID}/photos"
    photo_params = {
        "url": image_url,
        "published": False,
        "access_token": token,
    }
    resp = requests.post(photo_url, data=photo_params)
    result = resp.json()

    if "id" not in result:
        print(f"[FB] 上傳圖片失敗: {result}")
        return result

    photo_id = result["id"]
    print(f"[FB] 圖片上傳成功: {photo_id}")

    # Step 2: 發布貼文（含圖片）
    feed_url = f"{FB_API_BASE}/{FB_PAGE_ID}/feed"
    feed_params = {
        "message": caption,
        "attached_media": f'[{{"media_fbid":"{photo_id}"}}]',
        "access_token": token,
    }
    pub_resp = requests.post(feed_url, data=feed_params)
    pub_result = pub_resp.json()

    if "id" in pub_result:
        print(f"[FB] 貼文發布成功！Post ID: {pub_result['id']}")
    else:
        print(f"[FB] 貼文發布失敗: {pub_result}")

    return pub_result


def post_fb_text(caption: str) -> dict:
    """發布純文字貼文（無圖片）"""
    token = _get_page_token()

    feed_url = f"{FB_API_BASE}/{FB_PAGE_ID}/feed"
    feed_params = {
        "message": caption,
        "access_token": token,
    }
    resp = requests.post(feed_url, data=feed_params)
    result = resp.json()

    if "id" in result:
        print(f"[FB] 純文字貼文發布成功！Post ID: {result['id']}")
    else:
        print(f"[FB] 純文字貼文失敗: {result}")

    return result


def check_fb_page() -> dict:
    """確認粉專 token 是否有效"""
    try:
        token = _get_page_token()
    except ValueError as e:
        return {"error": str(e)}

    url = f"{FB_API_BASE}/{FB_PAGE_ID}"
    params = {
        "fields": "id,name,fan_count",
        "access_token": token,
    }
    resp = requests.get(url, params=params)
    return resp.json()
