"""
旅遊特價資料模組
提供每日旅遊主題和模擬特價資訊
（未來可串接真實 API）
"""
import random
from datetime import datetime

# 熱門目的地清單
DESTINATIONS = [
    {"name": "日本東京", "emoji": "🗾", "season": "全年"},
    {"name": "日本大阪", "emoji": "🏯", "season": "全年"},
    {"name": "日本北海道", "emoji": "❄️", "season": "冬季"},
    {"name": "韓國首爾", "emoji": "🇰🇷", "season": "全年"},
    {"name": "泰國曼谷", "emoji": "🇹🇭", "season": "全年"},
    {"name": "泰國清邁", "emoji": "🌸", "season": "全年"},
    {"name": "越南峴港", "emoji": "🏖️", "season": "全年"},
    {"name": "新加坡", "emoji": "🦁", "season": "全年"},
    {"name": "香港", "emoji": "🏙️", "season": "全年"},
    {"name": "峇里島", "emoji": "🌴", "season": "全年"},
    {"name": "沖繩", "emoji": "🌊", "season": "夏季"},
    {"name": "菲律賓長灘島", "emoji": "🏄", "season": "全年"},
]

# 旅遊攻略主題（用於漲粉貼文）
TRAVEL_TIPS = [
    "日本自由行必備 App 推薦",
    "韓國購物必去的平價店家",
    "泰國曼谷必吃平價美食",
    "出國前必做的 5 件事",
    "省錢訂機票的秘訣",
    "行李箱打包技巧大公開",
    "旅遊保險該怎麼買",
    "日本交通 IC 卡完整攻略",
    "沖繩租車自駕完全指南",
    "峇里島必去景點推薦",
    "新加坡 3 天 2 夜行程規劃",
    "首爾弘大逛街購物攻略",
]

# 模擬機票特價資料
FLIGHT_DEALS = [
    {"route": "台北→東京", "price": "NT$8,990", "airline": "長榮/華航"},
    {"route": "台北→首爾", "price": "NT$6,500", "airline": "韓亞/國泰"},
    {"route": "台北→曼谷", "price": "NT$7,200", "airline": "泰航/長榮"},
    {"route": "台北→大阪", "price": "NT$7,800", "airline": "樂桃/酷航"},
    {"route": "台北→新加坡", "price": "NT$8,500", "airline": "新航/捷星"},
    {"route": "台北→峴港", "price": "NT$6,800", "airline": "越捷/台越"},
    {"route": "台北→香港", "price": "NT$3,500", "airline": "港龍/國泰"},
    {"route": "台北→沖繩", "price": "NT$5,990", "airline": "樂桃/酷航"},
]


def get_daily_content() -> dict:
    """
    根據今天的日期決定發什麼內容
    奇數日：特價機票貼文
    偶數日：旅遊攻略貼文
    """
    day = datetime.now().day

    if day % 2 == 1:
        # 特價貼文
        dest = random.choice(DESTINATIONS)
        deal = random.choice(FLIGHT_DEALS)
        return {
            "type": "deal",
            "destination": dest["name"],
            "emoji": dest["emoji"],
            "deal_info": f"{deal['route']} 來回 {deal['price']}（{deal['airline']}）",
        }
    else:
        # 攻略貼文
        tip = random.choice(TRAVEL_TIPS)
        return {
            "type": "tip",
            "topic": tip,
        }


def get_story_content() -> dict:
    """每天發 2 則限時動態用的內容"""
    stories = []
    for _ in range(2):
        dest = random.choice(DESTINATIONS)
        deal = random.choice(FLIGHT_DEALS)
        stories.append({
            "destination": dest["name"],
            "emoji": dest["emoji"],
            "deal_info": f"{deal['route']} 來回 {deal['price']}",
        })
    return stories


def get_image_url(destination: str, lock: int = None) -> str:
    """
    取得與目的地/主題相符的圖片直接網址
    使用 loremflickr.com（免費、無需 API key、圖片與關鍵字相符）
    """
    import requests

    keyword_map = {
        "東京": "tokyo,japan",
        "大阪": "osaka,japan",
        "北海道": "hokkaido,japan",
        "首爾": "seoul,korea",
        "曼谷": "bangkok,thailand",
        "清邁": "chiangmai,thailand",
        "峴港": "danang,vietnam",
        "新加坡": "singapore",
        "香港": "hongkong",
        "峇里島": "bali,indonesia",
        "沖繩": "okinawa,japan",
        "長灘島": "boracay,philippines",
        "旅遊": "travel,vacation",
        "機票": "airplane,travel",
        "攻略": "travel,adventure",
    }

    keyword = "travel,scenic"
    for key, val in keyword_map.items():
        if key in destination:
            keyword = val
            break

    try:
        lock_param = f"?lock={lock}" if lock else f"?lock={random.randint(1, 500)}"
        url = f"https://loremflickr.com/1080/1080/{keyword}{lock_param}"
        resp = requests.head(url, allow_redirects=True, timeout=10)
        if resp.status_code == 200:
            return resp.url
    except Exception:
        pass

    # 備用：picsum（穩定，但非主題圖）
    import hashlib
    seed = int(hashlib.md5(destination.encode()).hexdigest()[:8], 16) % 1000
    return f"https://picsum.photos/seed/{seed}/1080/1080"
