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
    """
    用 requests 模擬瀏覽器抓取公開 IG 帳號的貼文 alt text（縮圖描述）。
    失敗時 fallback 到 instaloader。
    """
    import requests
    from html.parser import HTMLParser

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

    # 方法一：requests 直接抓圖片 alt（Instagram 有時會在 meta 或圖片 alt 放 caption）
    try:
        r = requests.get(f"https://www.instagram.com/{username}/", headers=headers, timeout=15)
        if r.status_code == 200 and "og:description" in r.text:
            # 從 meta og:description 取得描述
            import re as _re
            metas = _re.findall(r'content="([^"]{30,})"', r.text)
            captions = [m for m in metas if len(m) > 30][:count]
            if captions:
                print(f"[Scraper] requests 方式成功，取得 {len(captions)} 則描述")
                return captions
    except Exception as e:
        print(f"[Scraper] requests 方式失敗：{e}")

    # 方法二：instaloader fallback
    try:
        L = instaloader.Instaloader(download_pictures=False, download_videos=False,
                                     download_video_thumbnails=False, download_geotags=False,
                                     download_comments=False, save_metadata=False, quiet=True)
        ig_user = os.getenv("SCRAPER_IG_USER", "")
        ig_pass = os.getenv("SCRAPER_IG_PASS", "")
        if ig_user and ig_pass:
            try:
                L.login(ig_user, ig_pass)
                print(f"[Scraper] 已登入 @{ig_user}")
            except Exception as e:
                print(f"[Scraper] 登入失敗：{e}")
        profile = instaloader.Profile.from_username(L.context, username)
        captions = []
        for post in profile.get_posts():
            if post.caption:
                captions.append(post.caption[:600])
            if len(captions) >= count:
                break
        return captions
    except Exception as e:
        print(f"[Scraper] instaloader 也失敗：{e}")
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



# ── @1336cryptoclub ICT 主題抓取 ──────────────────────────────────────────────

ICT_QUEUE_PATH  = os.path.join(os.path.dirname(__file__), "ict_topic_queue.json")
ICT_TARGET_ACCT = "1336cryptoclub"


def _extract_ict_topics(captions: list) -> list:
    """讓 Claude 從 @1336cryptoclub 貼文中提取 ICT/聰明錢教學主題"""
    if not captions:
        return []
    client = anthropic.Anthropic()
    sample = "\n---\n".join(captions[:10])
    prompt = f"""以下是 @1336cryptoclub（加密貨幣 ICT/聰明錢策略 IG 帳號）最近的貼文摘要：

{sample}

請根據這些貼文的主題方向，列出 8 個適合 WycBotAI 製作教學輪播的加密貨幣技術分析主題。
要求：
- 主題要跟 ICT、聰明錢、技術分析相關
- 每個主題格式：「主題名稱（英文/縮寫）」，例如「訂單塊（Order Block）」「公平價值缺口（FVG）」
- 繁體中文，具體有教學價值
- 只回傳 JSON 陣列，不要其他說明：["主題1", "主題2", ...]"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text
    m = re.search(r'\[.*\]', raw, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group())
    except Exception:
        return []


def refresh_1336_topics():
    """每週抓 @1336cryptoclub 最新貼文，更新 ICT 主題佇列"""
    print(f"[ICT Scraper] 抓取 @{ICT_TARGET_ACCT} 最新貼文...")
    captions = _fetch_captions(ICT_TARGET_ACCT, 12)
    if not captions:
        print("[ICT Scraper] 抓取失敗，保留現有佇列")
        return False

    topics = _extract_ict_topics(captions)
    if not topics:
        print("[ICT Scraper] 主題分析失敗")
        return False

    existing = []
    if os.path.exists(ICT_QUEUE_PATH):
        with open(ICT_QUEUE_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f).get("topics", [])

    combined = topics + [t for t in existing if t not in topics]
    queue = {"topics": combined[:30], "updated_at": datetime.datetime.now().isoformat()}
    with open(ICT_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    print(f"[ICT Scraper] 儲存 {len(queue['topics'])} 個主題")

    # ── 每週三抓完後，把本次新抓的主題完整列出 ──────────────────────────
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    sep = "=" * 50
    print(f"\n{sep}")
    print(f"[ICT Scraper] 本週抓取結果  {now_str}")
    print(f"本次從 @{ICT_TARGET_ACCT} 分析出 {len(topics)} 個主題：")
    for i, t in enumerate(topics, 1):
        print(f"  {i:02d}. {t}")
    print(sep + "\n")

    return True


def get_1336_topic() -> str:
    """
    從佇列取下一個 ICT 主題（取完一輪後從頭循環）。
    若佇列不存在，先嘗試 refresh，失敗則回傳 None。
    """
    if not os.path.exists(ICT_QUEUE_PATH):
        refresh_1336_topics()

    if not os.path.exists(ICT_QUEUE_PATH):
        return None

    with open(ICT_QUEUE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    topics = data.get("topics", [])
    if not topics:
        return None

    used_idx = data.get("used_idx", 0)
    topic = topics[used_idx % len(topics)]
    data["used_idx"] = (used_idx + 1) % len(topics)

    with open(ICT_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[ICT Scraper] 今日主題：{topic}")
    return topic


if __name__ == "__main__":
    refresh_topic_queue()
