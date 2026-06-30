# -*- coding: utf-8 -*-
import os, urllib.request, json, tweepy
from datetime import datetime, timezone, timedelta

API_KEY             = os.getenv("TWITTER_API_KEY",            "j2FKBI0bJP3c1KOlrq4Uh0zsm")
API_KEY_SECRET      = os.getenv("TWITTER_API_KEY_SECRET",     "mpAymPkpoNXqgAf7pQKsjdUHFgaVru9NYmWbWkHCYj7QhtIDz6")
ACCESS_TOKEN        = os.getenv("TWITTER_ACCESS_TOKEN",       "1892680440185815042-kT98ZP3NGQfPlrzwjuE0SUy8SCwyw3")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET","uGFKxNrnUUOygidKfLDm3X4vyJSYSYvPNY0YRGKjzo39V")
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

def build_tweet():
    coins=[("BTCUSDT","BTC"),("ETHUSDT","ETH"),("SOLUSDT","SOL"),("DOGEUSDT","DOGE")]
    rows=[]; bull=0; bear=0
    for sym,name in coins:
        try:
            ps,rsi,up=_get_price_rsi_trend(sym)
            arr="▲" if up else "▼"
            trend="多" if up else "空"
            rows.append(f"{arr} #{name} ${ps}  RSI{rsi}  偏{trend}")
            if up: bull+=1
            else: bear+=1
        except: pass
    mood="偏多，可以留意做多的機會喔" if bull>=3 else ("偏空，先降低倉位、等訊號比較安全" if bear>=3 else "幣種分歧，選強勢幣做多就好")
    t=f"AI自動交易 每日掃描 {_twn_now()} TWN\n\n"
    t+="\n".join(rows)
    t+=f"\n\n今天大盤{mood}\n\n"
    t+=f"有興趣跟單的話，來這裡看免費訊號\n"
    t+=f"👉 t.me/wycbotai\n\n"
    t+=f"還在手動盯盤？試試 AI 自動交易\n"
    t+=f"WycBotAI 24小時執行策略，Telegram 即時通知\n"
    t+=f"入門版 $30/月 👉 wycbotai-production.up.railway.app\n\n"
    t+=f"BingX 開戶折扣連結 👉 {BINGX_URL}\n\n"
    t+=f"#crypto #BTC #ETH #合約交易 #加密貨幣 #AlgoTrading"
    return t

def post_daily_analysis():
    tweet=build_tweet()
    print(f"推文內容:\n{tweet}\n字數:{len(tweet)}")
    try:
        r=_client().create_tweet(text=tweet)
        print(f"成功 ID:{r.data['id']}")
        return True
    except Exception as e:
        print(f"失敗:{e}")
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


if __name__=="__main__":
    post_daily_analysis()
