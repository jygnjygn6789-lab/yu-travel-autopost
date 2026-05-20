"""
WycBotAI IG 自動發文主程式
帳號：@wycbotai（加密貨幣技術分析教學）
排程：
  每天 01:00 UTC (09:00 台灣) → 指標教學輪播（週一三五日）/ 金句避雷（週二四六）
  每天 03:00 UTC (11:00 台灣) → K 線形態輪播
  每天 05:00 UTC (13:00 台灣) → ICT 聰明錢輪播
  每天 08:00 UTC (16:00 台灣) → 技術指標教學 Reel
  每週三 00:00 UTC (08:00 台灣) → 抓 @1336cryptoclub ICT 主題
"""
import os
import sys
import time
import schedule
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from ig_poster import post_wycbotai_carousel, post_wycbotai_reel
from img_uploader import upload_pil_image, upload_video


def _upload_cards_robust(cards: list, name: str) -> list:
    import requests as _req
    urls = []
    for i, card in enumerate(cards):
        url = None
        for attempt in range(5):
            url = upload_pil_image(card, f"{name}_{i}_r{attempt}.jpg")
            if not url:
                print(f"[上傳] Card {i} 第 {attempt+1} 次失敗，重試...")
                time.sleep(4)
                continue
            try:
                r = _req.head(url, timeout=10, allow_redirects=True)
                if r.status_code == 200:
                    break
                print(f"[上傳] Card {i} HEAD 回傳 {r.status_code}，重新上傳...")
                url = None
            except Exception as e:
                print(f"[上傳] Card {i} HEAD 檢查失敗：{e}，重新上傳...")
                url = None
            time.sleep(3)
        if url:
            urls.append(url)
            print(f"[上傳] Card {i} OK: {url}")
        else:
            print(f"[上傳] Card {i} 多次失敗，跳過")
    return urls


def _post_wycbotai_robust(slides: list, caption: str, name: str) -> dict:
    """上傳並用 WycBotAI IG 帳號發輪播（最多 3 輪重試）"""
    for round_n in range(3):
        urls = _upload_cards_robust(slides, f"{name}_r{round_n}")
        if len(urls) < 2:
            print(f"[WycBotAI] 可用圖片不足 2 張，取消發文")
            return {}
        result = post_wycbotai_carousel(urls, caption)
        if "id" in result:
            return result
        err = result.get("error", {})
        code = err.get("code") if isinstance(err, dict) else None
        subcode = err.get("error_subcode") if isinstance(err, dict) else None
        if code == 4:
            print(f"[WycBotAI] Rate limit，今日停止發文")
            return result
        elif subcode in (2207052, 2207003):
            print(f"[WycBotAI] 圖片問題（第 {round_n+1} 輪），重新上傳...")
            continue
        else:
            print(f"[WycBotAI] 發文失敗：{err}")
            return result
    return result


def _update_keyword_trigger(indicator_short: str):
    """發文成功後，把當日指標關鍵字加入 keyword_triggers.json"""
    import json as _json
    triggers_path = os.path.join(os.path.dirname(__file__), "keyword_triggers.json")
    try:
        with open(triggers_path, "r", encoding="utf-8") as f:
            triggers = _json.load(f)
    except Exception:
        triggers = []

    existing_keywords = [t.get("keyword", "").upper() for t in triggers]
    if indicator_short.upper() not in existing_keywords:
        dm_msg = (
            f"感謝你的留言！\n\n"
            f"這裡是 WycBotAI 免費體驗連結：\nhttps://wycbotai.com\n\n"
            f"我們的 AI 每日自動掃描 {indicator_short} 信號，幫你找到最佳進場時機。\n\n"
            f"有任何問題歡迎繼續留言！"
        )
        triggers.append({"keyword": indicator_short, "dm_message": dm_msg, "public_reply": ""})
        with open(triggers_path, "w", encoding="utf-8") as f:
            _json.dump(triggers, f, ensure_ascii=False, indent=2)
        print(f"[WycBotAI] 已新增關鍵字觸發：{indicator_short}")


def run_wycbotai_indicator(indicator_name: str = None):
    """發布 WycBotAI 每日指標教學輪播"""
    from indicator_tutorial_gen import generate_indicator_post, get_today_indicator
    name = indicator_name or get_today_indicator()
    print(f"\n[WycBotAI] 生成「{name}」教學輪播...")
    slides, caption = generate_indicator_post(name)
    result = _post_wycbotai_robust(slides, caption, name="wyc_indicator")
    if result.get("id"):
        print(f"[WycBotAI] IG 發文成功！ID: {result['id']}")
        kw = name.split("（")[0].strip()
        _update_keyword_trigger(kw)
    else:
        print(f"[WycBotAI] 發文失敗：{result}")


def run_wycbotai_alt():
    """週二四六發佈：華爾街金句 or 新手常犯的錯"""
    from wycbotai_alt_gen import get_today_alt_post
    slides, caption = get_today_alt_post()
    result = _post_wycbotai_robust(slides, caption, name="wyc_alt")
    if result.get("id"):
        print(f"[WycBotAI Alt] IG 發文成功！ID: {result['id']}")
    else:
        print(f"[WycBotAI Alt] 發文失敗：{result}")


def run_wycbotai_kline():
    """發布 K 線形態教學輪播（每次隨機選 3 種形態）"""
    import random
    from kline_pattern_gen import generate_kline_post, KLINE_PATTERNS
    keys = random.sample(list(KLINE_PATTERNS.keys()), min(3, len(KLINE_PATTERNS)))
    print(f"\n[K線] 生成形態：{keys}")
    slides, caption = generate_kline_post(keys)
    result = _post_wycbotai_robust(slides, caption, name="wyc_kline")
    if result.get("id"):
        print(f"[K線] 發文成功！ID: {result['id']}")
    else:
        print(f"[K線] 發文失敗：{result}")


def run_wycbotai_ict(topic: str = None):
    """發布 ICT/聰明錢風格輪播"""
    from ict_post_gen import generate_ict_post
    from ig_scraper import get_1336_topic
    name = topic or get_1336_topic() or "斐波那契回調（Fibonacci Retracement）"
    print(f"\n[ICT] 生成「{name}」輪播...")
    slides, caption = generate_ict_post(name)
    result = _post_wycbotai_robust(slides, caption, name="wyc_ict")
    if result.get("id"):
        print(f"[ICT] IG 發文成功！ID: {result['id']}")
    else:
        print(f"[ICT] 發文失敗：{result}")


def run_wycbotai_reel(indicator_name: str = None):
    """發 WycBotAI 技術指標教學 Reel"""
    from reel_indicator_gen import generate_indicator_reel
    print(f"\n[WycBotAI Reel] 開始生成指標教學 Reel...")
    try:
        video_path, caption = generate_indicator_reel(indicator_name)
    except Exception as e:
        print(f"[WycBotAI Reel] 生成失敗：{e}")
        return

    print(f"[WycBotAI Reel] 上傳影片...")
    video_url = upload_video(video_path)
    if not video_url:
        print("[WycBotAI Reel] 影片上傳失敗，跳過")
        return

    result = post_wycbotai_reel(video_url, caption)
    if result.get("id"):
        print(f"[WycBotAI Reel] 發布成功！ID: {result['id']}")
    else:
        print(f"[WycBotAI Reel] 發布失敗：{result}")


if __name__ == "__main__":
    print("\n[WycBotAI] 開始排程自動發文...")
    print("每天 01:00 UTC (09:00 台灣) → 指標教學輪播 / 金句避雷")
    print("每天 03:00 UTC (11:00 台灣) → K 線形態輪播")
    print("每天 05:00 UTC (13:00 台灣) → ICT 聰明錢輪播")
    print("每天 08:00 UTC (16:00 台灣) → 技術指標教學 Reel")
    print("每週三 00:00 UTC (08:00 台灣) → 抓 @1336cryptoclub ICT 主題")
    print("按 Ctrl+C 停止\n")

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        opt = sys.argv[2] if len(sys.argv) > 2 else None
        if arg == "indicator":
            run_wycbotai_indicator(opt)
        elif arg == "alt":
            run_wycbotai_alt()
        elif arg == "kline":
            from kline_pattern_gen import generate_kline_post
            keys = sys.argv[2:] if len(sys.argv) > 2 else None
            slides, caption = generate_kline_post(keys)
            result = _post_wycbotai_robust(slides, caption, name="wyc_kline")
            print(result)
        elif arg == "ict":
            run_wycbotai_ict(opt)
        elif arg == "reel":
            run_wycbotai_reel(opt)
        elif arg == "scrape":
            from ig_scraper import refresh_1336_topics
            refresh_1336_topics()
    else:
        import datetime as _dt

        def _wycbotai_daily():
            dow = _dt.date.today().isoweekday()  # 1=Mon … 7=Sun
            if dow in (1, 3, 5, 7):
                run_wycbotai_indicator()
            else:
                run_wycbotai_alt()

        from ig_scraper import refresh_1336_topics

        schedule.every().day.at("01:00").do(_wycbotai_daily)
        schedule.every().day.at("03:00").do(run_wycbotai_kline)
        schedule.every().day.at("05:00").do(run_wycbotai_ict)
        schedule.every().day.at("08:00").do(run_wycbotai_reel)
        schedule.every().wednesday.at("00:00").do(refresh_1336_topics)

        while True:
            schedule.run_pending()
            time.sleep(60)
