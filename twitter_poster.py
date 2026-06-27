"""
twitter_poster.py — 自動發推文到 @wl00312862
每天發 BTC/ETH 市場分析 + BingX referral
"""
import os
import tweepy
from datetime import datetime, timezone, timedelta

# Twitter API 憑證
API_KEY             = os.getenv("TW_API_KEY",    "j2FKBI0bJP3c1KOlrq4Uh0zsm")
API_SECRET          = os.getenv("TW_API_SECRET", "mpAymPkpoNXqgAf7pQKsjdUHFgaVru9NYmWbWkHCYj7QhtIDz6")
ACCESS_TOKEN        = os.getenv("TW_ACCESS_TOKEN",  "1892680440185815042-kT98ZP3NGQfPlrzwjuE0SUy8SCwyw3")
ACCESS_TOKEN_SECRET = os.getenv("TW_ACCESS_TOKEN_SECRET", "uGFKxNrnUUOygidKfLDm3X4vyJSYSYvPNY0YRGKjzo39V")

BINGX_URL = "https://bingxdao.com/invite/LKUUM8/"
TG_CHANNEL = "https://t.me/wycbotai"

def _client():
    return tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
    )

def _twn_now():
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%m/%d %H:%M")

def post_tweet(text: str) -> dict:
    """發推文，回傳 {ok, tweet_id, error}"""
    try:
        client = _client()
        resp = client.create_tweet(text=text)
        tweet_id = resp.data["id"]
        print(f"[Twitter] 推文成功 ID={tweet_id}")
        return {"ok": True, "tweet_id": tweet_id}
    except Exception as e:
        print(f"[Twitter] 推文失敗: {e}")
        return {"ok": False, "error": str(e)}


def build_daily_tweet(btc_price: float, btc_trend: str, btc_rsi: float,
                       eth_price: float, eth_trend: str, eth_rsi: float) -> str:
    """生成每日市場分析推文"""
    btc_emoji = "📈" if btc_trend == "多頭" else "📉" if btc_trend == "空頭" else "↔️"
    eth_emoji = "📈" if eth_trend == "多頭" else "📉" if eth_trend == "空頭" else "↔️"

    return (
        f"📊 加密市場早報 {_twn_now()} TWN\n\n"
        f"#BTC ${btc_price:,.0f}\n"
        f"{btc_emoji} 趨勢：{btc_trend}｜RSI {btc_rsi:.0f}\n\n"
        f"#ETH ${eth_price:,.0f}\n"
        f"{eth_emoji} 趨勢：{eth_trend}｜RSI {eth_rsi:.0f}\n\n"
        f"🔔 免費訊號頻道 {TG_CHANNEL}\n"
        f"🏦 BingX 開戶折扣 {BINGX_URL}\n\n"
        f"#crypto #比特幣 #加密貨幣 #合約交易 #BTC #ETH"
    )


def build_signal_tweet(symbol: str, side: str, price: float,
                        sl: float, tp: float, strategy: str) -> str:
    """生成訊號推文"""
    side_str = "做多 ▲" if side.lower() == "buy" else "做空 ▼"
    sl_pct = abs(price - sl) / price * 100 if sl else 0
    tp_pct = abs(tp - price) / price * 100 if tp else 0

    return (
        f"🤖 AI訊號 #{symbol}\n\n"
        f"{side_str}\n"
        f"進場：${price:,.4f}\n"
        f"止損：${sl:,.4f} (-{sl_pct:.1f}%)\n"
        f"止盈：${tp:,.4f} (+{tp_pct:.1f}%)\n\n"
        f"策略：{strategy}\n\n"
        f"🔔 更多訊號 {TG_CHANNEL}\n"
        f"🏦 BingX 開戶 {BINGX_URL}\n\n"
        f"#crypto #{symbol} #合約交易 #CryptoSignals"
    )


if __name__ == "__main__":
    # 快速測試
    result = post_tweet(
        f"🤖 WycBotAI 加密貨幣訊號頻道正式上線！\n\n"
        f"✅ 每日 BTC/ETH 市場分析\n"
        f"✅ AI 量化策略即時訊號\n"
        f"✅ 完全免費追蹤\n\n"
        f"🔔 Telegram 頻道 {TG_CHANNEL}\n"
        f"🏦 BingX 開戶折扣 {BINGX_URL}\n\n"
        f"#crypto #BTC #ETH #加密貨幣 #合約交易"
    )
    print(result)
