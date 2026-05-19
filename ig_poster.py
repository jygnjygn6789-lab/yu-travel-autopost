"""
Instagram Graph API 發文模組
支援一般貼文和限時動態
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

IG_USER_ID = os.getenv("IG_USER_ID")
ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
BASE_URL = "https://graph.instagram.com/v21.0"

# WycBotAI 專用帳號（連結到 Wyvbotai FB 粉專，使用 FB_PAGE_TOKEN 發文）
WYCBOTAI_IG_USER_ID = os.getenv("WYCBOTAI_IG_USER_ID")
FB_BASE_URL = "https://graph.facebook.com/v21.0"


def refresh_token_if_needed():
    """檢查並刷新 token（長效 token 有效期 60 天）"""
    app_id = os.getenv("FB_APP_ID")
    app_secret = os.getenv("FB_APP_SECRET")
    token = os.getenv("IG_ACCESS_TOKEN")

    url = f"{BASE_URL}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": token,
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    if "access_token" in data:
        new_token = data["access_token"]
        # 更新 .env 中的 token
        _update_env_token(new_token)
        print(f"Token 刷新成功，有效期: {data.get('expires_in', '不明')} 秒")
        return new_token
    else:
        print(f"Token 刷新失敗: {data}")
        return token


def _update_env_token(new_token: str):
    """更新 .env 檔案中的 IG_ACCESS_TOKEN"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(env_path, "w", encoding="utf-8") as f:
        for line in lines:
            if line.startswith("IG_ACCESS_TOKEN="):
                f.write(f"IG_ACCESS_TOKEN={new_token}\n")
            else:
                f.write(line)
    # 更新當前環境變數
    os.environ["IG_ACCESS_TOKEN"] = new_token


def post_feed(image_url: str, caption: str) -> dict:
    """
    發布一般貼文（圖片 + 文字）
    image_url: 必須是公開可訪問的圖片 URL
    caption: 貼文文字（含 hashtag）
    """
    token = os.getenv("IG_ACCESS_TOKEN")

    # Step 1: 建立媒體容器
    create_url = f"{BASE_URL}/{IG_USER_ID}/media"
    create_params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    }
    resp = requests.post(create_url, data=create_params)
    result = resp.json()

    if "id" not in result:
        print(f"建立媒體容器失敗: {result}")
        return result

    container_id = result["id"]
    print(f"媒體容器建立成功: {container_id}")

    # Step 1.5: 等待 Instagram 處理圖片
    import time
    for attempt in range(10):
        time.sleep(5)
        status_url = f"{BASE_URL}/{container_id}"
        status_resp = requests.get(status_url, params={"fields": "status_code", "access_token": token})
        status = status_resp.json().get("status_code", "")
        print(f"圖片處理狀態: {status}")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            print("圖片處理失敗")
            return status_resp.json()
    else:
        print("圖片處理超時")

    # Step 2: 發布媒體容器
    publish_url = f"{BASE_URL}/{IG_USER_ID}/media_publish"
    publish_params = {
        "creation_id": container_id,
        "access_token": token,
    }
    pub_resp = requests.post(publish_url, data=publish_params)
    pub_result = pub_resp.json()

    if "id" in pub_result:
        print(f"貼文發布成功！Post ID: {pub_result['id']}")
    else:
        print(f"貼文發布失敗: {pub_result}")

    return pub_result


def post_carousel(image_urls: list, caption: str) -> dict:
    """
    發布輪播貼文（2-10 張圖）
    image_urls: 公開 URL 清單
    """
    token = os.getenv("IG_ACCESS_TOKEN")

    # Step 1: 建立每張圖的媒體容器
    container_ids = []
    for i, url in enumerate(image_urls):
        resp = requests.post(
            f"{BASE_URL}/{IG_USER_ID}/media",
            data={"image_url": url, "is_carousel_item": "true", "access_token": token},
        )
        result = resp.json()
        if "id" not in result:
            print(f"輪播項目 {i+1} 建立失敗: {result}")
            return result
        container_ids.append(result["id"])
        print(f"輪播項目 {i+1}/{len(image_urls)} 建立成功: {result['id']}")

    # Step 2: 建立輪播容器
    import time
    time.sleep(3)
    resp = requests.post(
        f"{BASE_URL}/{IG_USER_ID}/media",
        data={
            "media_type": "CAROUSEL",
            "caption": caption,
            "children": ",".join(container_ids),
            "access_token": token,
        },
    )
    result = resp.json()
    if "id" not in result:
        print(f"輪播容器建立失敗: {result}")
        return result

    carousel_id = result["id"]
    print(f"輪播容器建立成功: {carousel_id}")

    # Step 3: 等待處理完成
    for _ in range(12):
        time.sleep(5)
        status = requests.get(
            f"{BASE_URL}/{carousel_id}",
            params={"fields": "status_code", "access_token": token},
        ).json().get("status_code", "")
        print(f"輪播處理狀態: {status}")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            return {"error": "圖片處理失敗"}

    # Step 4: 發布
    pub = requests.post(
        f"{BASE_URL}/{IG_USER_ID}/media_publish",
        data={"creation_id": carousel_id, "access_token": token},
    ).json()

    if "id" in pub:
        print(f"輪播貼文發布成功！Post ID: {pub['id']}")
    else:
        print(f"輪播貼文發布失敗: {pub}")

    return pub


def post_story(image_url: str = None, link_url: str = None, source_media_id: str = None) -> dict:
    """
    發布限時動態
    source_media_id: 直接引用已發布的貼文 ID（分享貼文到限時動態）
    image_url: 若沒有 source_media_id，用圖片 URL 建立
    link_url: 加入可點擊的 link sticker
    """
    token = os.getenv("IG_ACCESS_TOKEN")

    # Step 1: 建立 Story 媒體容器
    create_url = f"{BASE_URL}/{IG_USER_ID}/media"
    if source_media_id:
        create_params = {
            "media_type": "STORIES",
            "source_media_id": source_media_id,
            "access_token": token,
        }
    else:
        create_params = {
            "image_url": image_url,
            "media_type": "STORIES",
            "access_token": token,
        }
    if link_url:
        import json
        create_params["link_sticker"] = json.dumps({"link": link_url})
    resp = requests.post(create_url, data=create_params)
    result = resp.json()

    if "id" not in result:
        print(f"建立 Story 容器失敗: {result}")
        return result

    container_id = result["id"]
    print(f"Story 容器建立成功: {container_id}")

    # Step 1.5: 等待處理完成
    import time
    for _ in range(10):
        time.sleep(5)
        status = requests.get(
            f"{BASE_URL}/{container_id}",
            params={"fields": "status_code", "access_token": token},
        ).json().get("status_code", "")
        print(f"Story 處理狀態: {status}")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            return {"error": "Story 圖片處理失敗"}

    # Step 2: 發布
    publish_url = f"{BASE_URL}/{IG_USER_ID}/media_publish"
    publish_params = {
        "creation_id": container_id,
        "access_token": token,
    }
    pub_resp = requests.post(publish_url, data=publish_params)
    pub_result = pub_resp.json()

    if "id" in pub_result:
        print(f"限時動態發布成功！Story ID: {pub_result['id']}")
    else:
        print(f"限時動態發布失敗: {pub_result}")

    return pub_result


def post_reel(video_url: str, caption: str) -> dict:
    """
    發布 Reels 影片
    video_url: 必須是公開可訪問的 .mp4 URL
    """
    import time
    token = os.getenv("IG_ACCESS_TOKEN")

    # Step 1: 建立 Reel 媒體容器
    resp = requests.post(
        f"{BASE_URL}/{IG_USER_ID}/media",
        data={
            "video_url": video_url,
            "media_type": "REELS",
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
    )
    result = resp.json()
    if "id" not in result:
        print(f"建立 Reel 容器失敗: {result}")
        return result

    container_id = result["id"]
    print(f"Reel 容器建立成功: {container_id}")

    # Step 2: 等待處理完成
    for _ in range(24):  # 最多等 4 分鐘
        time.sleep(10)
        status = requests.get(
            f"{BASE_URL}/{container_id}",
            params={"fields": "status_code", "access_token": token},
        ).json().get("status_code", "")
        print(f"Reel 處理狀態: {status}")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            return {"error": "Reel 影片處理失敗"}

    # Step 3: 發布
    pub = requests.post(
        f"{BASE_URL}/{IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": token},
    ).json()

    if "id" in pub:
        print(f"Reel 發布成功！Post ID: {pub['id']}")
    else:
        print(f"Reel 發布失敗: {pub}")

    return pub


def get_account_info() -> dict:
    """取得 IG 帳號資訊（用來驗證 token 是否有效）"""
    token = os.getenv("IG_ACCESS_TOKEN")
    url = f"{BASE_URL}/{IG_USER_ID}"
    params = {
        "fields": "id,username,followers_count,media_count",
        "access_token": token,
    }
    resp = requests.get(url, params=params)
    return resp.json()


def post_wycbotai_reel(video_url: str, caption: str) -> dict:
    """
    用 FB_PAGE_TOKEN 發布 Reel 到 WycBotAI IG 帳號
    video_url: 公開可存取的 .mp4 URL
    """
    import time
    token = os.getenv("FB_PAGE_TOKEN")
    ig_id = os.getenv("WYCBOTAI_IG_USER_ID")

    if not ig_id:
        return {"error": "WYCBOTAI_IG_USER_ID 未設定"}
    if not token:
        return {"error": "FB_PAGE_TOKEN 未設定"}

    resp = requests.post(
        f"{FB_BASE_URL}/{ig_id}/media",
        data={
            "video_url": video_url,
            "media_type": "REELS",
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
    )
    result = resp.json()
    if "id" not in result:
        print(f"建立 WycBotAI Reel 容器失敗: {result}")
        return result

    container_id = result["id"]
    print(f"WycBotAI Reel 容器建立成功: {container_id}")

    for _ in range(24):
        time.sleep(10)
        status = requests.get(
            f"{FB_BASE_URL}/{container_id}",
            params={"fields": "status_code", "access_token": token},
        ).json().get("status_code", "")
        print(f"WycBotAI Reel 處理狀態: {status}")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            return {"error": "Reel 影片處理失敗"}

    pub = requests.post(
        f"{FB_BASE_URL}/{ig_id}/media_publish",
        data={"creation_id": container_id, "access_token": token},
    ).json()

    if "id" in pub:
        print(f"WycBotAI Reel 發布成功！Post ID: {pub['id']}")
    else:
        print(f"WycBotAI Reel 發布失敗: {pub}")

    return pub


def post_wycbotai_carousel(image_urls: list, caption: str) -> dict:
    """
    用 FB_PAGE_TOKEN 發布輪播到 WycBotAI IG 帳號（WYCBOTAI_IG_USER_ID）
    """
    import time
    token = os.getenv("FB_PAGE_TOKEN")
    ig_id = os.getenv("WYCBOTAI_IG_USER_ID")

    if not ig_id:
        return {"error": "WYCBOTAI_IG_USER_ID 未設定，請執行 get_fb_token.py"}
    if not token:
        return {"error": "FB_PAGE_TOKEN 未設定"}

    # Step 1: 建立每張圖的媒體容器
    container_ids = []
    for i, url in enumerate(image_urls):
        resp = requests.post(
            f"{FB_BASE_URL}/{ig_id}/media",
            data={"image_url": url, "is_carousel_item": "true", "access_token": token},
        )
        result = resp.json()
        if "id" not in result:
            print(f"輪播項目 {i+1} 建立失敗: {result}")
            return result
        container_ids.append(result["id"])
        print(f"輪播項目 {i+1}/{len(image_urls)} 建立成功: {result['id']}")

    # Step 2: 建立輪播容器
    time.sleep(3)
    resp = requests.post(
        f"{FB_BASE_URL}/{ig_id}/media",
        data={
            "media_type": "CAROUSEL",
            "caption": caption,
            "children": ",".join(container_ids),
            "access_token": token,
        },
    )
    result = resp.json()
    if "id" not in result:
        print(f"輪播容器建立失敗: {result}")
        return result

    carousel_id = result["id"]
    print(f"輪播容器建立成功: {carousel_id}")

    # Step 3: 等待處理完成
    for _ in range(12):
        time.sleep(5)
        status = requests.get(
            f"{FB_BASE_URL}/{carousel_id}",
            params={"fields": "status_code", "access_token": token},
        ).json().get("status_code", "")
        print(f"輪播處理狀態: {status}")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            return {"error": "圖片處理失敗"}

    # Step 4: 發布
    pub = requests.post(
        f"{FB_BASE_URL}/{ig_id}/media_publish",
        data={"creation_id": carousel_id, "access_token": token},
    ).json()

    if "id" in pub:
        print(f"WycBotAI 輪播發布成功！Post ID: {pub['id']}")
    else:
        print(f"WycBotAI 輪播發布失敗: {pub}")

    return pub
