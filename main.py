"""
Yu的出國旅遊大全 - IG 自動發文主程式
每天自動發：1 則貼文 + 2 則限時動態
"""
import os
import sys
import schedule
import time
from dotenv import load_dotenv

# Fix Windows CP950 encoding issues with emoji
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from ig_poster import post_feed, post_carousel, post_story, post_reel, get_account_info, refresh_token_if_needed
from content_gen import generate_travel_post, generate_travel_tip_post
from travel_data import get_daily_content, get_story_content, get_image_url
from fb_poster import post_fb_feed, check_fb_page
from thaihi_guide_gen import generate_thaihi_guide
from tips_guide_gen import generate_tips_guide
from linkinbio_guide_gen import generate_linkinbio_guide
from image_gen import generate_tip_carousel
from img_uploader import upload_pil_image, upload_video
from comment_bot import run_comment_bot

load_dotenv()

LINKINBIO = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"


def _upload_cards_robust(cards: list, name: str) -> list:
    """
    上傳所有卡片，每張最多重試 5 次，並在上傳後用 HEAD 確認 URL 可存取。
    回傳成功的 URL 清單。
    """
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
            # 確認 URL 可被外部存取
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


def _post_carousel_robust(cards: list, caption: str, name: str = "card") -> dict:
    """
    上傳並發輪播，自動處理：
    - URL 被 IG 拒絕 → 重新上傳再試（最多 3 輪）
    - Rate limit → 直接停止（不重試，避免重複發文）
    """
    for round_n in range(3):
        urls = _upload_cards_robust(cards, f"{name}_r{round_n}")
        if len(urls) < 2:
            print("[發文] 可用圖片不足 2 張，取消發文")
            return {}

        result = post_carousel(urls, caption)
        if "id" in result:
            return result

        err = result.get("error", {})
        code = err.get("code")
        subcode = err.get("error_subcode")

        if code == 4:  # Rate limit — 停止，不重試，避免重複發文
            print(f"[發文] Rate limit（每日發文上限），今日停止發文")
            return result
        elif subcode == 2207052:  # URL 被拒 → 重新上傳再試
            print(f"[發文] URL 被拒（第 {round_n+1} 輪），重新上傳全部圖片...")
            continue
        else:
            print(f"[發文] 發文失敗：{err.get('message')}")
            return result

    return result

    return result


def run_daily_post():
    """每天早上 10:00 發一則貼文"""
    print("\n[貼文] 開始生成今日貼文...")
    content = get_daily_content()

    if content["type"] == "linkinbio":
        print("[貼文] 生成主頁連結使用指南（7 張）...")
        cards, caption = generate_linkinbio_guide()
    elif content["type"] == "deal":
        destination = content["destination"]
        # 去掉國家前綴，例如「日本東京」→「東京」
        for prefix in ["日本", "韓國", "泰國", "菲律賓", "越南"]:
            destination = destination.replace(prefix, "")
        print(f"[貼文] 生成 {destination} 金色風格懶人包（7 張）...")
        cards, caption = generate_thaihi_guide(destination)
    else:
        topic = content["topic"]
        print(f"[貼文] 生成「{topic}」金色風格懶人包（7 張）...")
        cards, caption = generate_tips_guide(topic)

    print(f"[貼文] 文案預覽:\n{caption[:100]}...")
    print(f"[貼文] 上傳並發文（自動重試）...")
    post_result = _post_carousel_robust(cards, caption, name="daily")
    if not post_result.get("id"):
        print("[貼文] 最終發文失敗，跳過")
        return
    print(f"[貼文] IG 結果: {post_result}")
    image_urls = []  # 補齊後面 last_post.json 需要的變數
    # 重新上傳一張封面圖供 story 使用
    cover_url = upload_pil_image(cards[0], "cover_story.jpg")
    if cover_url:
        image_urls.append(cover_url)

    # 存今日貼文 ID 供限時動態引用
    import json
    cover_img = image_urls[0] if image_urls else ""
    last_post = {"post_id": post_result.get("id"), "image_url": cover_img}
    with open(os.path.join(os.path.dirname(__file__), "last_post.json"), "w", encoding="utf-8") as f:
        json.dump(last_post, f, ensure_ascii=False)

    # 同步發 FB（若有設定 FB_PAGE_TOKEN）
    if os.getenv("FB_PAGE_TOKEN"):
        fb_result = post_fb_feed(image_urls[0], caption)
        print(f"[貼文] FB 結果: {fb_result}")
    else:
        print("[貼文] FB_PAGE_TOKEN 未設定，跳過 FB 發文")


def run_daily_stories():
    """每天下午 7:00 發 2 則限時動態（引用今日貼文圖片）"""
    import json
    print("\n[限時動態] 開始發今日限時動態...")
    linkinbio_url = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"

    # 讀取今日貼文 ID
    last_post_path = os.path.join(os.path.dirname(__file__), "last_post.json")
    if os.path.exists(last_post_path):
        with open(last_post_path, "r", encoding="utf-8") as f:
            last_post = json.load(f)
        post_id = last_post.get("post_id")
        fallback_image = last_post.get("image_url")
        print(f"[限時動態] 引用今日貼文 ID: {post_id}")
    else:
        post_id = None
        fallback_image = get_image_url("旅遊")
        print(f"[限時動態] 找不到今日貼文，使用隨機圖")

    # 發 2 則限時動態（用今日貼文第一張圖，帶 linkinbio 連結）
    story_image = fallback_image or get_image_url("旅遊")
    for i in range(1, 3):
        print(f"[限時動態 {i}/2] 發布中...")
        result = post_story(image_url=story_image, link_url=linkinbio_url)
        print(f"[限時動態 {i}/2] 結果: {result}")
        if i < 2:
            time.sleep(10)


def run_daily_reel():
    """每天下午 3:00 發一則 Reel（同日目的地）"""
    import json as _json, re, anthropic
    from reel_gen import generate_spot_reel

    print("\n[Reel] 開始生成今日 Reel...")
    content = get_daily_content()
    dest_full = content.get("destination", "東京")
    dest = dest_full
    for prefix in ["日本", "韓國", "泰國", "菲律賓", "越南"]:
        dest = dest.replace(prefix, "")

    # 用 Claude Haiku 快速生成 4 個亮點 + 交通資訊
    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": f"""為「{dest}」生成 Reel 內容，JSON 格式回應：
{{"highlights": ["亮點1（15字內）","亮點2","亮點3","亮點4"], "route": "大眾運輸路線", "station": "下車站名", "walk": "步行時間"}}
繁體中文，具體實用，台灣人視角。"""}]
        )
        raw = msg.content[0].text
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        data = _json.loads(m.group()) if m else {}
    except Exception as e:
        print(f"[Reel] Claude 生成失敗：{e}")
        data = {}

    highlights = data.get("highlights", [
        f"{dest}必去景點推薦", f"{dest}美食必吃清單",
        f"{dest}交通省錢攻略", f"{dest}住宿最佳區域"
    ])
    transport = {
        "route": data.get("route", "當地大眾運輸"),
        "station": data.get("station", "市中心站"),
        "walk": data.get("walk", "5 分鐘"),
    }

    video_path = generate_spot_reel(
        spot_name=dest,
        location=dest_full,
        label="旅遊攻略",
        highlights=highlights,
        transport=transport,
    )

    print(f"[Reel] 上傳影片...")
    video_url = upload_video(video_path)
    if not video_url:
        print("[Reel] 影片上傳失敗，跳過")
        return

    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"
    caption = f"""✈️ {dest}旅遊攻略 懶人包 Reel 版！

必看亮點全在這支影片裡
完整攻略 + 機票比價連結在主頁 👇
{linkinbio}

❤️ 按讚支持更多旅遊分享
🔔 追蹤 @taiwan.travel.deals 不錯過優惠
💬 留言「{dest}」取得完整攻略

#{dest}旅遊 #{dest}攻略 #{dest}懶人包 #旅遊Reels #台灣旅遊 #旅遊省錢"""

    result = post_reel(video_url, caption)
    print(f"[Reel] 結果: {result}")


def check_account():
    """啟動時確認帳號和 token 狀態"""
    print("正在確認 IG 帳號狀態...")
    info = get_account_info()
    if "username" in info:
        print(f"帳號確認成功: @{info['username']}")
        print(f"粉絲數: {info.get('followers_count', '不明')}")
        print(f"貼文數: {info.get('media_count', '不明')}")
    else:
        print(f"帳號確認失敗: {info}")
        print("請重新產生 Token 並更新 .env 中的 IG_ACCESS_TOKEN")

    # 確認 FB 粉專狀態
    if os.getenv("FB_PAGE_TOKEN"):
        fb_info = check_fb_page()
        if "name" in fb_info:
            print(f"FB 粉專確認成功: {fb_info['name']} (粉絲數: {fb_info.get('fan_count', '不明')})")
        else:
            print(f"FB 粉專確認失敗: {fb_info}")
    else:
        print("FB_PAGE_TOKEN 未設定，FB 自動發文停用")


def manual_post():
    """手動立即發一篇貼文（測試用）"""
    print("\n=== 手動發文模式 ===")
    run_daily_post()


def manual_story():
    """手動立即發限時動態（測試用）"""
    print("\n=== 手動發限時動態模式 ===")
    run_daily_stories()


def manual_linkinbio_post():
    """手動發主頁連結懶人包輪播"""
    print("\n=== 主頁連結懶人包輪播 ===")
    cards, caption = generate_linkinbio_guide()
    print(f"[貼文] 文案預覽:\n{caption[:100]}...")
    post_result = _post_carousel_robust(cards, caption, name="linkinbio")
    if post_result.get("id"):
        print(f"[貼文] 成功！ID: {post_result['id']}")
        import json
        cover_url = upload_pil_image(cards[0], "cover_story.jpg")
        last_post = {"post_id": post_result.get("id"), "image_url": cover_url or ""}
        with open(os.path.join(os.path.dirname(__file__), "last_post.json"), "w", encoding="utf-8") as f:
            json.dump(last_post, f, ensure_ascii=False)
    else:
        print(f"[貼文] 失敗：{post_result}")


def manual_linkinbio_reel():
    """手動發主頁連結 Reel"""
    import json as _json, re as _re, anthropic as _anthropic
    from reel_gen import generate_spot_reel

    print("\n=== 主頁連結 Reel ===")
    highlights = [
        "機票比價一鍵找最低價",
        "Klook / KKday 行程優惠整合",
        "旅遊保險快速比較選購",
        "eSIM 出發前線上買免換卡",
        "每週更新限時特價資訊",
        "全中文介面，台灣人設計",
    ]
    transport = {
        "route": "IG 主頁點連結",
        "station": "taiwan.travel.deals",
        "walk": "完全免費",
    }
    video_path = generate_spot_reel(
        spot_name="主頁連結攻略",
        location="台灣出國必備",
        label="旅遊優惠",
        highlights=highlights,
        transport=transport,
    )
    print("[Reel] 上傳影片...")
    video_url = upload_video(video_path)
    if not video_url:
        print("[Reel] 影片上傳失敗")
        return
    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"
    caption = f"""🔗 主頁連結裡面藏了什麼？

很多人追蹤了不知道連結可以幹嘛
其實裡面整合了 6 個出國必備工具 👆

✈️ 機票比價｜🎫 Klook｜🗺️ KKday
🛡️ 旅遊保險｜📶 eSIM｜🔥 本週特價

全部免費使用，出國前點一次就夠：
{linkinbio}

❤️ 覺得實用幫我按讚
🔔 追蹤 @taiwan.travel.deals 不錯過優惠
💬 留言告訴我你最常用哪個功能？

#旅遊優惠 #機票比價 #Klook #KKday #旅遊保險 #eSIM #台灣旅遊 #出國攻略 #懶人包"""

    result = post_reel(video_url, caption)
    print(f"[Reel] 結果: {result}")


if __name__ == "__main__":
    import sys

    # 確認帳號
    check_account()

    if len(sys.argv) > 1:
        if sys.argv[1] == "post":
            manual_post()
        elif sys.argv[1] == "story":
            manual_story()
        elif sys.argv[1] == "refresh":
            refresh_token_if_needed()
        elif sys.argv[1] == "linkinbio_post":
            manual_linkinbio_post()
        elif sys.argv[1] == "linkinbio_reel":
            manual_linkinbio_reel()
    else:
        print("\n開始排程自動發文...")
        print("每天 10:00 自動發懶人包輪播（金色風格）")
        print("每天 15:00 自動發 Reel 影片")
        print("每天 19:00 自動發 2 則限時動態")
        print("每 30 分鐘自動掃描留言（按讚+回覆）")
        print("按 Ctrl+C 停止\n")

        schedule.every().day.at("10:00").do(run_daily_post)
        schedule.every().day.at("15:00").do(run_daily_reel)
        schedule.every().day.at("19:00").do(run_daily_stories)
        schedule.every(30).minutes.do(run_comment_bot)

        while True:
            schedule.run_pending()
            time.sleep(60)
