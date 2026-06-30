# -*- coding: utf-8 -*-
"""
Threads 自動發文模組
發文流程：
  1. 建立媒體容器 POST /v1.0/{user_id}/threads
  2. 發布           POST /v1.0/{user_id}/threads_publish
"""
import os, time, requests

THREADS_USER_ID = os.getenv("THREADS_USER_ID", "")
THREADS_TOKEN   = os.getenv("THREADS_ACCESS_TOKEN", "")
BASE_URL        = "https://graph.threads.net/v1.0"
SITE_URL        = "wycbotai-production.up.railway.app"
BINGX_URL       = "bingxdao.com/invite/LKUUM8/"


def _create_container(text: str) -> str | None:
    r = requests.post(
        f"{BASE_URL}/{THREADS_USER_ID}/threads",
        params={"media_type": "TEXT", "text": text, "access_token": THREADS_TOKEN},
        timeout=15,
    )
    data = r.json()
    if "id" in data:
        return data["id"]
    print(f"[Threads] 建立容器失敗: {data}")
    return None


def _publish_container(creation_id: str) -> str | None:
    r = requests.post(
        f"{BASE_URL}/{THREADS_USER_ID}/threads_publish",
        params={"creation_id": creation_id, "access_token": THREADS_TOKEN},
        timeout=15,
    )
    data = r.json()
    if "id" in data:
        return data["id"]
    print(f"[Threads] 發布失敗: {data}")
    return None


def post_text(text: str) -> str | None:
    """發一則 Threads 文字貼文，回傳 post id 或 None"""
    if not THREADS_USER_ID or not THREADS_TOKEN:
        print("[Threads] 未設定 THREADS_USER_ID / THREADS_ACCESS_TOKEN，跳過")
        return None
    cid = _create_container(text)
    if not cid:
        return None
    time.sleep(3)
    return _publish_container(cid)


def build_threads_post(rows: list, mood: str, bull_coins: list, bear_coins: list) -> str:
    t  = "📊 加密市場每日掃描\n\n"
    t += "\n".join(rows)
    t += f"\n\n大盤{mood}\n\n"
    if bull_coins:
        t += f"多頭偏強：{' '.join(bull_coins)}\n"
    if bear_coins:
        t += f"空頭偏強：{' '.join(bear_coins)}\n"
    t += "\n🤖 想讓 AI 幫你自動執行交易？\n"
    t += f"WycBotAI 入門版 $30/月\n"
    t += f"👉 {SITE_URL}\n\n"
    t += f"📩 每日訊號免費看 👉 t.me/wycbotai\n"
    t += f"BingX 開戶折扣 👉 {BINGX_URL}\n\n"
    t += "#crypto #BTC #ETH #加密貨幣 #AlgoTrading #量化交易"
    return t


if __name__ == "__main__":
    test = (
        "WycBotAI — AI 量化交易機器人\n\n"
        "24小時自動執行交易策略，不用守盤\n"
        "• EMA x RSI 信號自動進場\n"
        "• 動態止損止盈\n"
        "• Telegram 即時推播\n\n"
        f"入門版 $30/月 👉 {SITE_URL}\n\n"
        "#crypto #AlgoTrading #量化交易"
    )
    pid = post_text(test)
    print(f"測試發文結果: {pid}")
