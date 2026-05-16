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

# 出國注意事項主題（星期二、四、六）
TRAVEL_TIPS = [
    "旅遊保險",
    "航空公司怎麼選",
    "國際駕照申請與租車",
    "搭廉航注意事項",
    "行李打包與托運規定",
    "海外信用卡與換匯攻略",
    "eSIM 選購完整攻略",
    "機場快速通關技巧",
    "海外緊急應變指南",
    "出國前必做準備清單",
    "海外醫療與看病流程",
    "訂機票省錢完整攻略",
    "訂旅館比價攻略",
    "出國必備旅遊 App",
    "護照 簽證 申請流程",
    "海外行動上網完整攻略",
    "旅遊詐騙常見手法防範",
    "台灣出發最划算機場交通",
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
    根據星期幾決定發什麼內容：
    星期一（weekday 0）              → 主頁連結使用懶人包
    星期三、五、日（weekday 2,4,6）  → 旅遊目的地懶人包
    星期二、四、六（weekday 1,3,5）  → 出國注意事項懶人包
    用日期做 seed，同一天多次呼叫結果相同。
    """
    today = datetime.now()
    weekday = today.weekday()   # 0=Mon … 6=Sun
    seed = today.year * 10000 + today.month * 100 + today.day
    rng = random.Random(seed)

    if weekday == 0:               # 一 → 主頁連結懶人包
        return {"type": "linkinbio"}
    elif weekday in (2, 4, 6):     # 三、五、日 → 目的地
        dest = rng.choice(DESTINATIONS)
        deal = rng.choice(FLIGHT_DEALS)
        return {
            "type": "deal",
            "destination": dest["name"],
            "emoji": dest["emoji"],
            "deal_info": f"{deal['route']} 來回 {deal['price']}（{deal['airline']}）",
        }
    else:                          # 二、四、六 → 出國注意事項
        tip = rng.choice(TRAVEL_TIPS)
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
