"""
HeyGen AI 影片生成模組
自動生成旅遊 IG Reels：AI 主播 + 中文配音 + 字幕
"""
import os
import time
import requests
from dotenv import load_dotenv
import anthropic

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEADERS = {"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"}
BASE_URL = "https://api.heygen.com"

# 預設頭像（Lina 休閒風，適合旅遊帳號）
DEFAULT_AVATAR_ID = "Lina_Casual_Front_public"
# 中文語音 ID（女聲）
DEFAULT_VOICE_ID = "735c507fdc844be3b1528dd33f7dfb2a"

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def generate_reel_script(destination: str, deal_info: str = "", topic: str = "") -> str:
    """用 Claude 生成 30 秒 Reels 口播稿（繁中）"""
    if deal_info:
        prompt = f"""你是台灣旅遊 IG 帳號「Yu的出國旅遊大全」的主播。
請寫一段 30 秒的旅遊特價短影音口播稿：

目的地：{destination}
特價資訊：{deal_info}

格式要求：
- 開頭 3 秒：強力吸引注意（問句或驚嘆）
- 中間介紹特價重點（價格、目的地亮點）
- 結尾：「連結在主頁，馬上搶訂！」
- 全程繁體中文，口語化，活潑有親和力
- 約 100-120 個字（對應 30 秒語速）
- 直接輸出口播稿，不要標題說明"""
    else:
        prompt = f"""你是台灣旅遊 IG 帳號「Yu的出國旅遊大全」的主播。
請寫一段 30 秒的旅遊攻略短影音口播稿：

主題：{topic or destination}

格式要求：
- 開頭 3 秒：用問句吸引注意
- 列出 3 個最實用的重點
- 結尾：「更多攻略追蹤我們，連結在主頁！」
- 全程繁體中文，口語化，像朋友分享
- 約 100-120 個字（對應 30 秒語速）
- 直接輸出口播稿，不要標題說明"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def create_video(script: str, avatar_id: str = DEFAULT_AVATAR_ID, voice_id: str = DEFAULT_VOICE_ID) -> str:
    """呼叫 HeyGen API 建立影片，回傳 video_id"""
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                    "voice_id": voice_id,
                    "speed": 1.0,
                },
                "background": {
                    "type": "color",
                    "value": "#1a0a2e",  # 深紫色品牌背景
                },
            }
        ],
        "dimension": {"width": 1080, "height": 1920},  # 9:16 Reels 格式
        "caption": True,  # 自動字幕
    }

    resp = requests.post(f"{BASE_URL}/v2/video/generate", headers=HEADERS, json=payload, timeout=30)
    data = resp.json()

    if data.get("error"):
        raise Exception(f"HeyGen 建立影片失敗: {data['error']}")

    video_id = data.get("data", {}).get("video_id")
    if not video_id:
        raise Exception(f"未取得 video_id: {data}")

    print(f"[HeyGen] 影片建立中，video_id: {video_id}")
    return video_id


def wait_for_video(video_id: str, timeout: int = 300) -> str:
    """輪詢等待影片處理完成，回傳影片下載 URL"""
    print(f"[HeyGen] 等待影片處理...")
    start = time.time()

    while time.time() - start < timeout:
        resp = requests.get(
            f"{BASE_URL}/v1/video_status.get",
            headers=HEADERS,
            params={"video_id": video_id},
            timeout=15,
        )
        data = resp.json().get("data", {})
        status = data.get("status", "")
        print(f"[HeyGen] 狀態: {status}")

        if status == "completed":
            video_url = data.get("video_url")
            print(f"[HeyGen] 影片完成: {video_url}")
            return video_url
        elif status == "failed":
            raise Exception(f"HeyGen 影片處理失敗: {data.get('error')}")

        time.sleep(10)

    raise Exception("HeyGen 影片處理超時")


def download_video(video_url: str, save_path: str) -> str:
    """下載影片到本地"""
    resp = requests.get(video_url, timeout=60, stream=True)
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"[HeyGen] 影片已儲存: {save_path}")
    return save_path


def generate_travel_reel(destination: str, deal_info: str = "", topic: str = "") -> str:
    """
    主流程：生成腳本 → HeyGen 生成影片 → 回傳本地影片路徑
    """
    print(f"\n[HeyGen] 開始生成旅遊 Reel: {destination or topic}")

    # 1. 生成口播稿
    script = generate_reel_script(destination, deal_info, topic)
    print(f"[HeyGen] 腳本:\n{script}\n")

    # 2. 建立影片
    video_id = create_video(script)

    # 3. 等待完成
    video_url = wait_for_video(video_id)

    # 4. 下載到本地
    filename = f"reel_{destination or topic}_{int(time.time())}.mp4".replace(" ", "_")
    save_path = os.path.join(os.path.dirname(__file__), filename)
    download_video(video_url, save_path)

    return save_path
