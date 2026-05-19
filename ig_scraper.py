"""
每週自動抓 @japanuts 最新貼文，用 Claude 轉成台灣版話題清單，
存入 topic_queue.json，再 git commit + push 讓 Railway 拿到最新主題。

可獨立執行：python ig_scraper.py
也會被 main.py 每週一早上自動呼叫。
"""
import os, json, re, subprocess, sys, datetime
import instaloader
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

QUEUE_PATH  = os.path.join(os.path.dirname(__file__), "topic_queue.json")
TARGET_ACCT = "japanuts"
FETCH_COUNT = 15

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def _fetch_captions(username: str, count: int) -> list:
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        quiet=True,
    )
    # 用帳號登入，避免被 Instagram 封鎖
    ig_user = os.getenv("SCRAPER_IG_USER", "")
    ig_pass = os.getenv("SCRAPER_IG_PASS", "")
    if ig_user and ig_pass:
        try:
            L.login(ig_user, ig_pass)
            print(f"[Scraper] 已登入 @{ig_user}")
        except Exception as e:
            print(f"[Scraper] 登入失敗：{e}，嘗試匿名抓取")
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        captions = []
        for post in profile.get_posts():
            if post.caption:
                captions.append(post.caption[:600])
            if len(captions) >= count:
                break
        return captions
    except Exception as e:
        print(f"[Scraper] 抓取失敗：{e}")
        return []


def _extract_topics(captions: list) -> dict:
    if not captions:
        return {"destinations": [], "tips": []}

    client = anthropic.Anthropic()
    sample = "\n---\n".join(captions[:10])

    prompt = f"""以下是 @japanuts（日本旅遊 IG 帳號）最近的貼文摘要：

{sample}

請根據這些貼文的主題方向，為一個「台灣出發旅遊攻略」帳號（@taiwan.travel.deals）設計相似的話題清單。

規則：
1. destinations：8 個適合台灣人去的目的地（城市名），例如「日本京都」「泰國清邁」
2. tips：8 個具體實用的出國知識主題，要像 @japanuts 一樣具體時事，例如「日本退稅新制2026完整流程」「出國eSIM選購攻略」
3. 全部繁體中文，不要加「攻略」兩字結尾，主題名稱要像標題一樣吸引人

只回傳 JSON，不要其他說明：
{{"destinations": ["目的地1", ...], "tips": ["主題1", ...]}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    raw   = msg.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        return {"destinations": [], "tips": []}
    try:
        return json.loads(match.group())
    except Exception:
        return {"destinations": [], "tips": []}


def refresh_topic_queue():
    print(f"[Scraper] 抓取 @{TARGET_ACCT} 最新 {FETCH_COUNT} 篇貼文...")
    captions = _fetch_captions(TARGET_ACCT, FETCH_COUNT)

    if not captions:
        print("[Scraper] 抓取失敗，保留現有佇列")
        return False

    print(f"[Scraper] 抓到 {len(captions)} 篇，交給 Claude 分析主題...")
    topics = _extract_topics(captions)

    if not topics.get("destinations") and not topics.get("tips"):
        print("[Scraper] 分析失敗，保留現有佇列")
        return False

    existing = {"destinations": [], "tips": []}
    if os.path.exists(QUEUE_PATH):
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)

    def dedup(new_list, old_list):
        combined = new_list + [x for x in old_list if x not in new_list]
        return combined[:40]

    queue = {
        "destinations": dedup(topics["destinations"], existing.get("destinations", [])),
        "tips":         dedup(topics["tips"],         existing.get("tips", [])),
        "updated_at":   datetime.datetime.now().isoformat()
    }

    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    print(f"[Scraper] 儲存：{len(queue['destinations'])} 目的地、{len(queue['tips'])} 知識主題")

    repo = os.path.dirname(__file__)
    try:
        subprocess.run(["git", "add", "topic_queue.json"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "auto: refresh topic queue from @japanuts"], cwd=repo, check=True)
        subprocess.run(["git", "push"], cwd=repo, check=True)
        print("[Scraper] 已 push 到 Railway")
    except subprocess.CalledProcessError as e:
        print(f"[Scraper] git push 失敗：{e}")

    return True


if __name__ == "__main__":
    refresh_topic_queue()
