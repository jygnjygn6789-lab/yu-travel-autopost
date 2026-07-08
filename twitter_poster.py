# -*- coding: utf-8 -*-
import os, urllib.request, json, tweepy
from datetime import datetime, timezone, timedelta

API_KEY             = os.getenv("TWITTER_API_KEY",            "FM0d1gw13beFqBsP6vqgoUX43")
API_KEY_SECRET      = os.getenv("TWITTER_API_KEY_SECRET",     "z0gNPUSMhHMxDZHSKaTEi5tPprXvVCS5wdriT1xy1f9nGzAInl")
ACCESS_TOKEN        = os.getenv("TWITTER_ACCESS_TOKEN",       "1892680440185815042-TlF5tQ9loUyoMaoXmOSAEeeiA1gzcs")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET","bTNtIh1tWQqhUzB6ZVlEGU8jFEV5vqJkxdQv296wYn3N5")
BINGX_URL = "bingxdao.com/invite/LKUUM8/"

def _client():
    return tweepy.Client(consumer_key=API_KEY, consumer_secret=API_KEY_SECRET,
        access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)

def _twn_now():
    return (datetime.now(timezone.utc)+timedelta(hours=8)).strftime("%m/%d %H:%M")

def _get_price_rsi_trend(sym):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=4h&limit=60"
    c = [float(k[4]) for k in json.loads(urllib.request.urlopen(url, timeout=8).read())]
    k2=2/21; v=sum(c[:20])/20
    for x in c[20:]: v=x*k2+v*(1-k2)
    e20=v; k2=2/56; v=sum(c[:55])/55
    for x in c[55:]: v=x*k2+v*(1-k2)
    e55=v
    g=[max(c[i]-c[i-1],0) for i in range(1,len(c))]
    l=[max(c[i-1]-c[i],0) for i in range(1,len(c))]
    ag=sum(g[-14:])/14; al=sum(l[-14:])/14
    rsi=round(100-100/(1+ag/al)) if al else 100
    p=c[-1]
    ps=f"{p:,.0f}" if p>=1000 else (f"{p:.2f}" if p>=1 else f"{p:.4f}")
    return ps, rsi, e20>e55

def _fetch_market_data():
    """取得市場數據，回傳 (rows, mood, bull_coins, bear_coins)"""
    coins=[("BTCUSDT","BTC"),("ETHUSDT","ETH"),("SOLUSDT","SOL"),("DOGEUSDT","DOGE")]
    rows=[]; bull=0; bear=0; bull_coins=[]; bear_coins=[]
    for sym,name in coins:
        try:
            ps,rsi,up=_get_price_rsi_trend(sym)
            arr="▲" if up else "▼"
            trend="多" if up else "空"
            rows.append(f"{arr} {name} ${ps}  RSI{rsi}  偏{trend}")
            if up: bull+=1; bull_coins.append(f"#{name}")
            else: bear+=1; bear_coins.append(f"#{name}")
        except: pass
    mood="偏多，留意做多機會" if bull>=3 else ("偏空，降低倉位等訊號" if bear>=3 else "幣種分歧，選強勢幣操作")
    return rows, mood, bull_coins, bear_coins

def build_thread():
    """回傳 3 則串推內容的 list"""
    rows, mood, bull_coins, bear_coins = _fetch_market_data()

    # 第 1 則：Hook — 市場總覽
    t1  = f"📊 加密市場掃描 {_twn_now()} TWN\n\n"
    t1 += "\n".join(rows)
    t1 += f"\n\n大盤{mood} 👇 看完整分析"

    # 第 2 則：訊號詳解 + Telegram
    t2  = "🔍 今日訊號解讀\n\n"
    if bull_coins:
        t2 += f"多頭偏強：{' '.join(bull_coins)}\n"
    if bear_coins:
        t2 += f"空頭偏強：{' '.join(bear_coins)}\n"
    t2 += "\nRSI < 40 超賣、> 60 超買\nEMA20 > EMA55 = 短期趨勢向上\n\n"
    t2 += "📩 每日完整訊號（25+ 幣種）\n"
    t2 += f"👉 t.me/wycbotai\n\n"
    t2 += "#crypto #BTC #ETH #合約交易 #加密貨幣"

    # 第 3 則：WycBotAI 推廣
    t3  = "🤖 還在手動盯盤？\n\n"
    t3 += "WycBotAI 幫你 24 小時自動執行交易策略\n"
    t3 += "• EMA × RSI 自動偵測進場\n"
    t3 += "• 止盈止損全自動，不用守盤\n"
    t3 += "• Telegram 即時推播開平倉通知\n\n"
    t3 += "入門版 $30/月，3 個策略同時跑\n"
    t3 += f"👉 wycbotai-production.up.railway.app\n\n"
    t3 += f"BingX 開戶折扣 👉 {BINGX_URL}\n\n"
    t3 += "#AlgoTrading #量化交易 #被動收入"

    return [t1, t2, t3]

def build_single_tweet():
    """單則推文（包含市場掃描 + WycBotAI 推廣）"""
    rows, mood, bull_coins, bear_coins = _fetch_market_data()
    t  = f"📊 加密市場掃描 {_twn_now()} TWN\n\n"
    t += "\n".join(rows) if rows else "（資料取得中）"
    t += f"\n\n大盤{mood}\n\n"
    t += "🤖 AI 自動交易 wycbotai-production.up.railway.app\n"
    t += f"📩 免費訊號 t.me/wycbotai"
    return t

def post_daily_analysis():
    """發單則推文"""
    tweet = build_single_tweet()
    print(f"[Twitter] 推文字數:{len(tweet)}")
    try:
        r = _client().create_tweet(text=tweet)
        print(f"成功 ID:{r.data['id']}")
        return True
    except Exception as e:
        print(f"發文失敗:{e}")
        return False
        return False

def post_weekly_recruit():
    """每週三發一篇吸引入會的推文"""
    tweet = (
        "老實說，我也是散戶出身\n\n"
        "剛開始做合約的時候虧很慘\n"
        "後來才學會用 AI 自動交易來輔助判斷\n"
        "不是叫你全部交給機器，是讓 AI 幫你過濾雜訊\n\n"
        "現在每天把掃描結果整理出來免費分享\n"
        "BTC ETH SOL 等 25 個幣種\n"
        "有訊號才發，沒把握的不發\n\n"
        "歡迎來看看，完全免費\n"
        f"👉 t.me/wycbotai\n\n"
        "想在 BingX 開戶的話這裡有折扣\n"
        f"👉 {BINGX_URL}\n\n"
        "想讓 AI 幫你自動執行交易策略？\n"
        "WycBotAI 24小時自動開平倉，入門版 $30/月\n"
        f"👉 wycbotai-production.up.railway.app\n\n"
        "#crypto #BTC #加密貨幣 #合約交易 #被動收入 #AlgoTrading"
    )
    print(f"[Twitter] 週報推文:\n{tweet}")
    try:
        r = _client().create_tweet(text=tweet)
        print(f"[Twitter] 週報推文成功 ID:{r.data['id']}")
        return True
    except Exception as e:
        print(f"[Twitter] 週報推文失敗:{e}")
        return False


def post_daily_with_threads():
    """同時發 X Thread + Threads 貼文"""
    # X Thread
    post_daily_analysis()

    # Threads
    try:
        from threads_poster import build_threads_post, post_text
        rows, mood, bull_coins, bear_coins = _fetch_market_data()
        content = build_threads_post(rows, mood, bull_coins, bear_coins)
        pid = post_text(content)
        if pid:
            print(f"[Threads] 發文成功 ID:{pid}")
        else:
            print("[Threads] 發文失敗或未設定 Token")
    except Exception as e:
        print(f"[Threads] 例外: {e}")


if __name__=="__main__":
    post_daily_with_threads()
