"""
Claude AI 文案生成模組
自動生成旅遊 IG 貼文文案、hashtag
"""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

KLOOK_LINK = f"https://affiliate.klook.com/redirect?aid={os.getenv('KLOOK_AID')}&aff_adid={os.getenv('KLOOK_AFF_ADID')}&k_site=https%3A%2F%2Fwww.klook.com%2F"
KKDAY_LINK = f"https://www.kkday.com/?cid={os.getenv('KKDAY_CID')}"


def generate_travel_post(destination: str, deal_info: str, post_type: str = "feed") -> dict:
    """
    生成旅遊貼文文案
    destination: 目的地，例如 "日本東京"
    deal_info: 特價資訊，例如 "台北→東京 來回NT$8,990"
    post_type: "feed"（一般貼文）或 "story"（限時動態文案）
    """
    if post_type == "story":
        prompt = f"""你是台灣旅遊 IG 帳號「Yu的出國旅遊大全」的小編。
請為以下特價資訊生成一則限時動態文案（簡短有力，最多3行）：

目的地：{destination}
特價資訊：{deal_info}

格式要求：
- 第一行：吸睛標題（含emoji）
- 第二行：價格或優惠重點
- 第三行：行動呼籲（例如：點 bio 連結訂購！）
- 不要加 hashtag
- 用繁體中文"""
    else:
        prompt = f"""你是台灣旅遊 IG 帳號「Yu的出國旅遊大全」的小編。
請為以下旅遊資訊生成一則吸引人的 IG 貼文：

目的地：{destination}
特價資訊：{deal_info}
推廣連結說明：文案中提示讀者點 bio 連結訂購

格式要求：
1. 開頭要有吸睛的第一句話（含emoji）
2. 介紹旅遊亮點或省錢重點（3-5點）
3. 提醒讀者「連結在 bio」或「私訊我獲取連結」
4. 最後加上 15-20 個相關 hashtag（中英文混合）
5. 全文用繁體中文
6. 語氣活潑、像朋友推薦
7. 總長度約 150-250 字"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    caption = message.content[0].text

    return {
        "caption": caption,
        "klook_link": KLOOK_LINK,
        "kkday_link": KKDAY_LINK,
        "destination": destination,
        "deal_info": deal_info,
    }


def generate_travel_tip_post(topic: str) -> dict:
    """
    生成旅遊攻略貼文（非特價，用於漲粉）
    topic: 主題，例如 "日本自由行必備 App"
    """
    prompt = f"""你是台灣旅遊 IG 帳號「Yu的出國旅遊大全」的小編。
請生成一則關於「{topic}」的旅遊攻略貼文：

格式要求：
1. 開頭吸睛標題（含emoji）
2. 列出 5-7 個實用重點（每點一行，前面加 emoji）
3. 結尾：「更多優惠連結在 bio ⬆️ 記得追蹤不漏接！」
4. 加上 15-20 個 hashtag
5. 全文繁體中文，語氣像朋友分享
6. 總長度約 200-300 字"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "caption": message.content[0].text,
        "topic": topic,
    }
