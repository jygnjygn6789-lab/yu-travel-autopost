"""
泰嗨風格旅遊懶人包輪播圖生成模組
Bold graphic poster style: text-on-photo, gold accent elements, dark gradient
封面 + 機票/住宿/交通/美食/eSIM/注意事項 共 7 張
"""
import os
import json
import re
import anthropic
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pilmoji import Pilmoji
from dotenv import load_dotenv

from guide_gen import (
    ov_rounded, ov_rect, shadow, fb, fr, fe,
    wrap_text, LIGHT_TXT, SIZE,
)
from pexels import search_photos, download_image, get_travel_photo

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from font_paths import FONT_KAIU

# Gold accent palette
GOLD      = (245, 197, 0)
GOLD_DARK = (30, 20, 5)
WHITE     = (255, 255, 255)

TOPIC_ICONS = {
    "機票": "✈️", "住宿": "🏨", "交通": "🚌",
    "美食": "🍜", "eSIM": "📶", "注意事項": "⚠️",
}
TOPIC_EN = {
    "機票": "FLIGHTS", "住宿": "HOTEL", "交通": "TRANSPORT",
    "美食": "FOOD & DRINKS", "eSIM": "eSIM / DATA", "注意事項": "TRAVEL TIPS",
}

# 背景照片搜尋詞（針對主題，不帶城市名避免搜到不相關圖）
BG_QUERIES = {
    "機票": "airplane cockpit flight window",
    "住宿": "luxury hotel room bed interior",
    "交通": "city train metro commute transit",
    "美食": "restaurant food plating bowl",
    "eSIM": "smartphone travel digital roaming",
    "注意事項": "travel preparation passport safety",
}

# 照片條搜尋詞（2 組，各自不同方向）
STRIP_QUERIES = {
    "cover": [
        "{dest} city skyline aerial",
        "{dest} street food culture",
    ],
    "機票": [
        "airplane window seat clouds",
        "airport departure boarding gate",
    ],
    "住宿": [
        "luxury hotel room bed",
        "resort pool tropical relaxing",
    ],
    "交通": [
        "train station platform commuters",
        "metro subway underground city",
    ],
    "美食": [
        "{dest} local food restaurant dish",
        "street food market asia bowl",
    ],
    "eSIM": [
        "smartphone travel navigation map",
        "mobile roaming sim card tech",
    ],
    "注意事項": [
        "travel safety passport document",
        "tourist warning sign caution",
    ],
}


# ── 去重照片條 ────────────────────────────────────────────────────────────────

def _build_unique_strip(queries: list, strip_y: int, img: Image.Image) -> Image.Image:
    """
    下載最多 2 張不重複的照片（較大，500x210），橫排貼在 strip_y。
    只顯示拿到的唯一圖，不補重複。
    """
    used_urls: set = set()
    photos: list = []

    for q in queries[:2]:
        urls = search_photos(q, count=8, orientation="landscape")
        for url in urls:
            if url not in used_urls:
                used_urls.add(url)
                ph = download_image(url, (500, 210))
                photos.append(ph)
                break

    n = len(photos)
    if n == 0:
        return img

    pw, ph_h = 500, 210
    gap = 40
    total_w = pw * n + gap * (n - 1)
    start_x = (SIZE[0] - total_w) // 2

    for i, ph in enumerate(photos):
        px = start_x + i * (pw + gap)
        img.paste(ph.resize((pw, ph_h), Image.LANCZOS), (px, strip_y))

    return img


# ── 漸層疊加 ──────────────────────────────────────────────────────────────────

def _gradient_overlay(img: Image.Image, top_s=155, bot_s=195) -> Image.Image:
    w, h = img.size
    img_rgba = img.convert("RGBA")
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    top_h = 185
    for y in range(top_h):
        a = int(top_s * (1 - y / top_h) ** 0.7)
        d.line([(0, y), (w - 1, y)], fill=(0, 0, 0, a))

    bot_start = 700
    for y in range(bot_start, h):
        a = int(bot_s * ((y - bot_start) / (h - bot_start)) ** 0.5)
        d.line([(0, y), (w - 1, y)], fill=(0, 0, 0, a))

    return Image.alpha_composite(img_rgba, ov).convert("RGB")


# ── Claude 內容生成 ───────────────────────────────────────────────────────────

def _claude_generate(destination: str) -> dict:
    client = anthropic.Anthropic()
    prompt = f"""你是台灣旅遊達人，請用你所有知識為「{destination}」生成旅遊懶人包內容。

請以 JSON 格式回應，包含以下 6 個主題，每個主題 4 條建議：
{{
  "機票": ["建議1", "建議2", "建議3", "建議4"],
  "住宿": ["建議1", "建議2", "建議3", "建議4"],
  "交通": ["建議1", "建議2", "建議3", "建議4"],
  "美食": ["建議1", "建議2", "建議3", "建議4"],
  "eSIM": ["建議1", "建議2", "建議3", "建議4"],
  "注意事項": ["建議1", "建議2", "建議3", "建議4"]
}}

各主題規則（繁體中文，台灣人視角，越具體越好）：
- 機票：每條最多 22 字。包含：最佳訂票時機（提前幾週）、推薦航空公司名稱、有無直飛、大約票價範圍（NT$）
- 住宿：每條最多 22 字。包含：推薦區域名稱、預算範圍（每晚 NT$）、知名連鎖或品牌（如 APA、dormy inn、JOYTEL）
- 交通：每條最多 22 字。包含：具體交通工具名稱、票價（用當地貨幣或 NT$換算）、需要幾分鐘
- 美食：【重要】每條格式為「店名（原文）｜所在區｜必點：招牌菜名」，最多 30 字，要是真實知名店家
- eSIM：每條最多 22 字。包含：推薦品牌（Klook eSIM、Airalo、一嗨等）、天數方案、約 NT$ 費用
- 注意事項：每條最多 22 字。包含：具體禁忌/詐騙手法/當地法規、匯率參考（1 USD/JPY/KRW ≈ NT$?）"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1600,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    return json.loads(match.group()) if match else {}


# ── 封面 ──────────────────────────────────────────────────────────────────────

def _draw_cover(destination: str) -> Image.Image:
    bg = get_travel_photo(destination, "landmark scenic", SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.80)
    img = _gradient_overlay(bg, top_s=150, bot_s=180)
    draw = ImageDraw.Draw(img)
    w, h = SIZE

    # 浮水印
    draw.text((48, 36), "@taiwan.travel.deals", font=fr(22), fill=(255, 255, 255, 55))

    # 金色橫幅
    img = ov_rect(img, [0, 95, w, 178], (*GOLD, 245))
    draw = ImageDraw.Draw(img)
    band_text = f"帶你走進{destination}  出國不踩雷"
    fnt_band = fb(44)
    bb = draw.textbbox((0, 0), band_text, font=fnt_band)
    draw.text(((w - (bb[2] - bb[0])) // 2, 108), band_text, font=fnt_band, fill=GOLD_DARK)

    # 大標題（標楷體）
    fnt_title = ImageFont.truetype(FONT_KAIU, 122)
    draw = ImageDraw.Draw(img)
    bb2 = draw.textbbox((0, 0), destination, font=fnt_title)
    tx = (w - (bb2[2] - bb2[0])) // 2
    draw.text((tx + 4, 196), destination, font=fnt_title, fill=(0, 0, 0, 160))
    draw.text((tx, 192), destination, font=fnt_title, fill=WHITE)

    # 副標題
    sub = f"機票省錢 住好 吃好 交通不迷路 全在這"
    fnt_sub = fb(36)
    bb3 = draw.textbbox((0, 0), sub, font=fnt_sub)
    draw.text(((w - (bb3[2] - bb3[0])) // 2, 378), sub, font=fnt_sub, fill=(*GOLD, 235))

    # 主題藥丸格 2x3
    topics = list(TOPIC_ICONS.items())
    cols = 3
    cell_w = (w - 80) // cols
    cell_h = 106
    grid_top = 436
    pill_w = cell_w - 20
    fnt_pill = fb(32)

    for idx, (topic, icon) in enumerate(topics):
        col = idx % cols
        row = idx // cols
        cx = 40 + col * cell_w + cell_w // 2
        cy = grid_top + row * cell_h
        px = cx - pill_w // 2
        img = ov_rounded(img, [px, cy, px + pill_w, cy + 72], 36, (*GOLD, 230))
        label = f"{icon} {topic}"
        with Pilmoji(img) as pj:
            tw, _ = pj.getsize(label, font=fnt_pill)
            pj.text((cx - tw // 2, cy + 14), label, font=fnt_pill, fill=GOLD_DARK)
        draw = ImageDraw.Draw(img)

    # CTA 藥丸
    cta = "先收藏 ✨  出發前看這篇就夠了"
    fnt_cta = fb(36)
    with Pilmoji(img) as pj:
        cw, _ = pj.getsize(cta, font=fnt_cta)
    cx0 = (w - cw) // 2 - 24
    img = ov_rounded(img, [cx0, 672, cx0 + cw + 48, 672 + 58], 29, (*GOLD, 255))
    with Pilmoji(img) as pj:
        pj.text(((w - cw) // 2, 683), cta, font=fnt_cta, fill=GOLD_DARK)
    draw = ImageDraw.Draw(img)

    # 去重照片條
    qs = [q.format(dest=destination) for q in STRIP_QUERIES["cover"]]
    img = _build_unique_strip(qs, 760, img)

    # 互動 + 頁腳
    img = ov_rect(img, [0, 950, w, 1010], (28, 18, 10, 185))
    draw = ImageDraw.Draw(img)
    eng = "按讚  |  追蹤  |  留言城市名取得攻略"
    bb_e = draw.textbbox((0, 0), eng, font=fr(27))
    draw.text(((w - (bb_e[2] - bb_e[0])) // 2, 963), eng, font=fr(27), fill=(220, 200, 175))
    img = ov_rect(img, [0, 1010, w, h], (15, 9, 4, 220))
    draw = ImageDraw.Draw(img)
    draw.text((52, 1020), "@taiwan.travel.deals", font=fr(27), fill=LIGHT_TXT)
    draw.text((w - 200, 1020), "主頁連結 >>", font=fr(27), fill=(*GOLD, 220))

    return img


# ── 主題卡 ────────────────────────────────────────────────────────────────────

def _draw_topic_card(destination: str, topic: str, tips: list) -> Image.Image:
    icon  = TOPIC_ICONS.get(topic, "📌")
    en    = TOPIC_EN.get(topic, topic.upper())
    bg_q  = BG_QUERIES.get(topic, f"{destination} travel scenic")

    bg = get_travel_photo(bg_q, "", SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.72)
    img = _gradient_overlay(bg, top_s=165, bot_s=200)
    draw = ImageDraw.Draw(img)
    w, h = SIZE

    # 浮水印
    draw.text((48, 36), "@taiwan.travel.deals", font=fr(22), fill=(255, 255, 255, 55))

    # EN 標題（金色）
    fnt_en = fb(62)
    bb = draw.textbbox((0, 0), en, font=fnt_en)
    tx_en = (w - (bb[2] - bb[0])) // 2
    draw.text((tx_en + 3, 83), en, font=fnt_en, fill=(0, 0, 0, 140))
    draw.text((tx_en, 80), en, font=fnt_en, fill=(*GOLD,))

    # 中文主題名（標楷體，白色）
    fnt_zh = ImageFont.truetype(FONT_KAIU, 105)
    title_str = f"{icon} {topic}"
    with Pilmoji(img) as pj:
        tw, _ = pj.getsize(title_str, font=fnt_zh)
    tx_zh = (w - tw) // 2
    with Pilmoji(img) as pj:
        pj.text((tx_zh + 4, 164), title_str, font=fnt_zh, fill=(0, 0, 0))
    with Pilmoji(img) as pj:
        pj.text((tx_zh, 160), title_str, font=fnt_zh, fill=WHITE)
    draw = ImageDraw.Draw(img)

    # 金色標籤
    pill_text = f"{destination} {topic}攻略"
    fnt_pill = fb(34)
    bb_p = draw.textbbox((0, 0), pill_text, font=fnt_pill)
    pw_p = bb_p[2] - bb_p[0]
    px_p = (w - pw_p) // 2 - 22
    img = ov_rounded(img, [px_p, 338, px_p + pw_p + 44, 338 + 52], 26, (*GOLD, 240))
    draw = ImageDraw.Draw(img)
    bb_p2 = draw.textbbox((0, 0), pill_text, font=fnt_pill)
    draw.text(((w - (bb_p2[2] - bb_p2[0])) // 2, 348), pill_text, font=fnt_pill, fill=GOLD_DARK)

    # 條列 tips — 根據最長 tip 自動縮字
    max_len = max((len(t) for t in tips[:4]), default=0)
    if max_len > 26:
        fnt_tip, line_h = fr(33), 44
    elif max_len > 20:
        fnt_tip, line_h = fr(36), 48
    else:
        fnt_tip, line_h = fr(38), 50

    item_y = 415
    fnt_num = fb(28)
    CR = 20
    TIP_X = 58 + CR * 2 + 18

    for i, tip in enumerate(tips[:4]):
        cx_c = 58 + CR
        img = ov_rounded(
            img,
            [cx_c - CR, item_y + 4, cx_c + CR, item_y + 4 + CR * 2],
            CR, (*GOLD, 255)
        )
        draw = ImageDraw.Draw(img)
        num_str = str(i + 1)
        nb = draw.textbbox((0, 0), num_str, font=fnt_num)
        draw.text((cx_c - (nb[2] - nb[0]) // 2, item_y + 5), num_str, font=fnt_num, fill=GOLD_DARK)

        lines = wrap_text(tip, fnt_tip, w - TIP_X - 40, draw)
        for j, line in enumerate(lines[:2]):
            draw.text((TIP_X + 2, item_y + j * line_h + 2), line, font=fnt_tip, fill=(0, 0, 0, 130))
            draw.text((TIP_X, item_y + j * line_h), line, font=fnt_tip, fill=WHITE)

        item_y += max(len(lines[:2]), 1) * line_h + 16
        if item_y > 810:
            break

    # 去重照片條
    qs_raw = STRIP_QUERIES.get(topic, [f"{destination} travel", "tourism scenic", "travel adventure"])
    qs = [q.format(dest=destination) for q in qs_raw]
    img = _build_unique_strip(qs, 760, img)

    # 互動 + 頁腳
    img = ov_rect(img, [0, 950, w, 1010], (28, 18, 10, 185))
    draw = ImageDraw.Draw(img)
    eng = "按讚  |  追蹤  |  留言城市名取得攻略"
    bb_e = draw.textbbox((0, 0), eng, font=fr(27))
    draw.text(((w - (bb_e[2] - bb_e[0])) // 2, 963), eng, font=fr(27), fill=(220, 200, 175))
    img = ov_rect(img, [0, 1010, w, h], (15, 9, 4, 220))
    draw = ImageDraw.Draw(img)
    draw.text((52, 1020), "@taiwan.travel.deals", font=fr(27), fill=LIGHT_TXT)
    draw.text((w - 200, 1020), "主頁連結 >>", font=fr(27), fill=(*GOLD, 220))

    return img


# ── 主入口 ────────────────────────────────────────────────────────────────────

def generate_thaihi_guide(destination: str) -> tuple:
    """生成泰嗨風格懶人包輪播（7 張）+ caption"""
    print(f"[泰嗨懶人包] 用 Claude 生成 {destination} 內容...")
    data = _claude_generate(destination)

    cards = [_draw_cover(destination)]
    for topic in ["機票", "住宿", "交通", "美食", "eSIM", "注意事項"]:
        tips = data.get(topic, [f"{topic}資訊整理中...", "敬請期待"] * 2)
        print(f"  生成 {topic} 卡...")
        cards.append(_draw_topic_card(destination, topic, tips))

    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"
    caption = f"""🧳 帶你走進{destination}，出國不踩雷！

機票省錢 ✈️ 住哪最划算 🏨 交通怎麼搭 🚌
必吃美食 🍜 eSIM怎麼選 📶 注意事項 ⚠️
這些坑我幫你踩過了，你只要出發就好

🔗 機票比價 / Klook / KKday 優惠連結全在 👇
{linkinbio}

❤️ 按讚讓更多人看到這篇攻略
🔔 追蹤 @taiwan.travel.deals 不錯過最新優惠
💬 留言「{destination}」幫你整理完整行程

#{destination}旅遊 #{destination}懶人包 #{destination}攻略 #台灣旅遊 #旅遊攻略 #旅遊省錢 #懶人包"""

    return cards, caption
