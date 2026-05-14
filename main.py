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

from ig_poster import post_feed, post_carousel, post_story, get_account_info, refresh_token_if_needed
from content_gen import generate_travel_post, generate_travel_tip_post
from travel_data import get_daily_content, get_story_content, get_image_url
from fb_poster import post_fb_feed, check_fb_page
from image_gen import generate_deal_carousel, generate_tip_carousel
from img_uploader import upload_pil_image
from comment_bot import run_comment_bot

load_dotenv()


def run_daily_post():
    """每天早上 10:00 發一則貼文"""
    print("\n[貼文] 開始生成今日貼文...")
    content = get_daily_content()

    if content["type"] == "deal":
        destination = content["destination"]
        emoji = content["emoji"]
        deal_info = content["deal_info"]
        image_url = get_image_url(destination)
        result = generate_travel_post(destination, deal_info, post_type="feed")
        caption = result["caption"]
        highlights = result.get("highlights", [])

        print(f"[貼文] 生成輪播圖片...")
        cards = generate_deal_carousel(destination, emoji, deal_info, image_url, highlights)
    else:
        topic = content["topic"]
        image_url = get_image_url("旅遊")
        result = generate_travel_tip_post(topic)
        caption = result["caption"]
        highlights = result.get("highlights", [])

        print(f"[貼文] 生成輪播圖片...")
        cards = generate_tip_carousel(topic, image_url, highlights)

    # 上傳 3 張圖片
    print(f"[貼文] 上傳圖片到圖床...")
    image_urls = []
    for i, card in enumerate(cards):
        url = upload_pil_image(card, f"travel_card{i+1}.jpg")
        if url:
            image_urls.append(url)
            print(f"[貼文] 圖片 {i+1}: {url}")
        else:
            print(f"[貼文] 圖片 {i+1} 上傳失敗，跳過")

    print(f"[貼文] 文案預覽:\n{caption[:100]}...")

    # 發 IG（輪播）
    if len(image_urls) >= 2:
        post_result = post_carousel(image_urls, caption)
    elif len(image_urls) == 1:
        post_result = post_feed(image_urls[0], caption)
    else:
        print("[貼文] 沒有可用圖片，取消發文")
        return
    print(f"[貼文] IG 結果: {post_result}")

    # 同步發 FB（若有設定 FB_PAGE_TOKEN）
    if os.getenv("FB_PAGE_TOKEN"):
        fb_result = post_fb_feed(image_urls[0], caption)
        print(f"[貼文] FB 結果: {fb_result}")
    else:
        print("[貼文] FB_PAGE_TOKEN 未設定，跳過 FB 發文")


def run_daily_stories():
    """每天下午 7:00 發 2 則限時動態"""
    print("\n[限時動態] 開始生成今日限時動態...")
    stories = get_story_content()

    for i, story in enumerate(stories, 1):
        destination = story["destination"]
        deal_info = story["deal_info"]
        image_url = get_image_url(destination)

        print(f"[限時動態 {i}] 目的地: {destination}，圖片: {image_url}")
        result = post_story(image_url)
        print(f"[限時動態 {i}] 結果: {result}")

        if i < len(stories):
            time.sleep(5)  # 兩則之間間隔 5 秒


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
    else:
        print("\n開始排程自動發文...")
        print("每天 10:00 自動發貼文")
        print("每天 19:00 自動發限時動態")
        print("每 30 分鐘自動掃描留言（按讚+回覆）")
        print("按 Ctrl+C 停止\n")

        schedule.every().day.at("10:00").do(run_daily_post)
        schedule.every().day.at("19:00").do(run_daily_stories)
        schedule.every(30).minutes.do(run_comment_bot)

        while True:
            schedule.run_pending()
            time.sleep(60)
