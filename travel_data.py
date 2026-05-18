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

# 出國注意事項主題（星期二、四、六）— 每個主題單獨一篇深度攻略
TRAVEL_TIPS = [
    # 機票
    "機票比價：哪個平台最便宜",
    "廉航搭乘完整注意事項",
    "何時訂機票最便宜",
    "傳統航空 vs 廉航怎麼選",
    "機票退改票規則與技巧",
    # 旅遊保險
    "旅遊醫療險：保什麼、怎麼賠",
    "信用卡附旅遊保險夠用嗎",
    "行李遺失＆班機延誤怎麼理賠",
    # 住宿
    "訂旅館比價平台完整比較",
    "Airbnb 訂房完整注意事項",
    "青旅選擇與訂房技巧",
    # 交通
    "國際駕照申請完整流程",
    "租車攻略：選車、保險、還車",
    "機場到市區交通怎麼選",
    "JR Pass 使用完整攻略",
    # 通訊
    "出國 eSIM 完整選購攻略",
    "漫遊 vs eSIM vs 當地 SIM 比較",
    "海外 Wi-Fi 分享器 vs eSIM 比較",
    # 金錢
    "出國換匯省錢完整攻略",
    "海外消費推薦信用卡挑選指南",
    "Wise 轉帳＆海外消費完整指南",
    "東南亞現金 vs 刷卡怎麼選",
    # 行李
    "行李打包清單：不帶後悔的物品",
    "托運行李規定：各航空完整比較",
    "隨身行李液體規定完整攻略",
    # 簽證/護照
    "台灣護照辦理與更新完整流程",
    "免簽、落地簽、電子簽完整說明",
    "日本簽證申請步驟攻略",
    "東南亞各國入境規定比較",
    # 機場
    "桃園機場出境流程完整懶人包",
    "入境海關申報注意事項",
    "機場免稅店購物省錢攻略",
    "免費機場貴賓室使用完整指南",
    # 安全/緊急
    "護照遺失怎麼辦：完整應變流程",
    "海外急診看病流程與費用",
    "旅遊詐騙常見手法完整防範",
    # 省錢/工具
    "出國必備 App 完整清單 2025",
    "Klook vs KKday vs Viator 完整比較",
    "出國 10 個省錢技巧不能不知道",
    "Google Maps 出國離線使用攻略",
    "Google Translate 出國使用完整攻略",
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
