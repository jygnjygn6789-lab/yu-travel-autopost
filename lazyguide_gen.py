"""
旅遊懶人包輪播圖生成模組
奶油色風格（沿用 guide_gen 設計語言）
封面 + 機票/住宿/交通/美食/eSIM/注意事項 共 7 張
"""
import os
import json
import re
import anthropic
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pilmoji import Pilmoji
from dotenv import load_dotenv

# 直接借用 guide_gen 的 helper
from guide_gen import (
    warm_overlay, ov_rounded, ov_rect, shadow,
    fb, fr, fe, auto_icon, wrap_text, build_photo_strip,
    WARM_ORANGE, WARM_GOLD, CREAM, CREAM_DIM, DARK_TXT,
    MID_TXT, LIGHT_TXT, WARM_WHITE, RED_TAG, TEAL_TAG, SIZE,
)
from pexels import get_travel_photo

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

FONT_KAIU  = "C:/Windows/Fonts/kaiu.ttf"
FONT_BOLD  = "C:/Windows/Fonts/msjhbd.ttc"
FONT_REG   = "C:/Windows/Fonts/msjh.ttc"

TOPIC_ICONS = {
    "機票": "✈️",
    "住宿": "🏨",
    "交通": "🚌",
    "美食": "🍜",
    "eSIM": "📶",
    "注意事項": "⚠️",
}

TOPIC_COLORS = {
    "機票":   (58, 120, 195),
    "住宿":   (168, 88, 130),
    "交通":   (62, 148, 100),
    "美食":   WARM_ORANGE,
    "eSIM":   (88, 140, 178),
    "注意事項": (190, 72, 58),
}

TOPIC_QUERIES = {
    "機票":   "airplane flight",
    "住宿":   "hotel resort room",
    "交通":   "transport street city",
    "美食":   "local food cuisine",
    "eSIM":   "travel phone mobile",
    "注意事項": "travel tips warning",
}


def _claude_generate(destination: str) -> dict:
    client = anthropic.Anthropic()
    prompt = f"""你是台灣旅遊達人，請為「{destination}」生成旅遊懶人包內容。

請以 JSON 格式回應，包含以下 6 個主題，每個主題 4 條實用建議（每條最多 22 字）：
{{
  "機票": ["建議1", "建議2", "建議3", "建議4"],
  "住宿": ["建議1", "建議2", "建議3", "建議4"],
  "交通": ["建議1", "建議2", "建議3", "建議4"],
  "美食": ["建議1", "建議2", "建議3", "建議4"],
  "eSIM": ["建議1", "建議2", "建議3", "建議4"],
  "注意事項": ["建議1", "建議2", "建議3", "建議4"]
}}

規則：
- 內容具體實用，台灣人視角
- 機票：何時訂最便宜、哪個航空、有無直飛
- 住宿：哪個區域住最好、預算範圍
- 交通：機場到市區怎麼去、當地怎麼移動
- 美食：當地必吃、台灣吃不到的
- eSIM：推薦哪個、多少錢、怎麼設定
- 注意事項：當地禁忌、詐騙、天氣、匯率等
- 繁體中文"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    return json.loads(match.group()) if match else {}


def _draw_cover(destination: str) -> Image.Image:
    """封面卡：目的地照片 + 標楷體大標題 + 主題標籤列"""
    bg = get_travel_photo(destination, "landmark", SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.72)
    img = warm_overlay(bg)
    draw = ImageDraw.Draw(img)

    # 左上城市浮水印
    draw.text((52, 38), destination, font=fr(32), fill=(255, 252, 248, 55))

    # 標籤
    tag_str = "  \\ 旅遊懶人包 /  "
    fnt_tag = fb(34)
    bb = draw.textbbox((0, 0), tag_str, font=fnt_tag)
    tw = bb[2] - bb[0]
    tx = (SIZE[0] - tw) // 2
    img = ov_rounded(img, [tx - 16, 195, tx + tw + 16, 195 + (bb[3]-bb[1]) + 14], 20,
                     (*WARM_ORANGE, 220))
    draw = ImageDraw.Draw(img)
    draw.text((tx, 202), tag_str, font=fnt_tag, fill=WARM_WHITE)

    # 主標題（標楷體，大）
    fnt_title = ImageFont.truetype(FONT_KAIU, 118)
    bb2 = draw.textbbox((0, 0), destination, font=fnt_title)
    tx2 = (SIZE[0] - (bb2[2] - bb2[0])) // 2
    shadow(draw, (tx2, 255), destination, fnt_title, WARM_WHITE)

    # 副標題
    fnt_sub = fb(50)
    sub = "一篇搞定！出發前必收藏"
    bb3 = draw.textbbox((0, 0), sub, font=fnt_sub)
    tx3 = (SIZE[0] - (bb3[2]-bb3[0])) // 2
    draw.text((tx3, 420), sub, font=fnt_sub, fill=(*WARM_GOLD, 230))

    # 奶油色面板（6個主題標籤）
    panel_top = 498
    img = ov_rounded(img, [38, panel_top, SIZE[0]-38, 840], 16, (*CREAM, 228))
    draw = ImageDraw.Draw(img)

    # 面板 header
    hdr = "| 這次旅遊你需要的都在這裡 |"
    bb_h = draw.textbbox((0, 0), hdr, font=fr(30))
    hx = (SIZE[0] - (bb_h[2]-bb_h[0])) // 2
    draw.text((hx, panel_top + 14), hdr, font=fr(30), fill=LIGHT_TXT)
    draw.line([(60, panel_top+54), (SIZE[0]-60, panel_top+54)], fill=(*CREAM_DIM, 255), width=2)

    # 主題格 2x3
    topics = list(TOPIC_ICONS.items())
    cols, rows = 3, 2
    cell_w = (SIZE[0] - 76) // cols
    cell_h = 130
    fnt_ico = fe(44)
    fnt_lbl = fb(34)
    for idx, (topic, icon) in enumerate(topics):
        col = idx % cols
        row = idx // cols
        cx = 38 + col * cell_w + cell_w // 2
        cy = panel_top + 72 + row * cell_h
        color = TOPIC_COLORS[topic]
        with Pilmoji(img) as pj:
            ico_w, _ = pj.getsize(icon, font=fnt_ico)
            pj.text((cx - ico_w // 2, cy), icon, font=fnt_ico, fill=DARK_TXT)
        lbl_bb = draw.textbbox((0,0), topic, font=fnt_lbl)
        lbl_w = lbl_bb[2] - lbl_bb[0]
        draw.text((cx - lbl_w // 2, cy + 52), topic, font=fnt_lbl, fill=color)

    # 底部互動 + footer
    img = ov_rect(img, [0, 1010, SIZE[0], 1056], (28, 18, 10, 185))
    draw = ImageDraw.Draw(img)
    eng = "按讚  |  追蹤  |  留言城市名取得攻略"
    bb_e = draw.textbbox((0, 0), eng, font=fr(27))
    ex = (SIZE[0] - (bb_e[2]-bb_e[0])) // 2
    draw.text((ex, 1022), eng, font=fr(27), fill=(220, 200, 175))

    img = ov_rect(img, [0, 1056, SIZE[0], SIZE[1]], (15, 9, 4, 210))
    draw = ImageDraw.Draw(img)
    draw.text((52, 1063), "@taiwan.travel.deals", font=fr(27), fill=LIGHT_TXT)
    draw.text((SIZE[0]-200, 1063), "主頁連結 ▶", font=fr(27), fill=(*WARM_GOLD, 220))

    return img


def _draw_topic_card(destination: str, topic: str, tips: list) -> Image.Image:
    """主題卡：奶油色面板風格（沿用 guide_gen 設計）"""
    color = TOPIC_COLORS.get(topic, WARM_ORANGE)
    icon  = TOPIC_ICONS.get(topic, "📌")
    query = TOPIC_QUERIES.get(topic, destination)

    bg = get_travel_photo(f"{destination} {query}", "", SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.68)
    img = warm_overlay(bg)
    draw = ImageDraw.Draw(img)

    # 左上浮水印
    draw.text((52, 38), destination, font=fr(32), fill=(255, 252, 248, 55))

    # 標籤
    tag_str = f"  \\ {topic}攻略 /  "
    fnt_tag = fb(34)
    bb = draw.textbbox((0, 0), tag_str, font=fnt_tag)
    tw = bb[2] - bb[0]
    tx = (SIZE[0] - tw) // 2
    img = ov_rounded(img, [tx - 16, 195, tx + tw + 16, 195 + (bb[3]-bb[1]) + 14], 20,
                     (*color, 220))
    draw = ImageDraw.Draw(img)
    draw.text((tx, 202), tag_str, font=fnt_tag, fill=WARM_WHITE)

    # 大標題 icon + 主題名（標楷體）
    fnt_big  = ImageFont.truetype(FONT_KAIU, 110)
    title_str = f"{icon} {topic}"
    with Pilmoji(img) as pj:
        tb = pj.getsize(title_str, font=fnt_big)
        tx2 = (SIZE[0] - tb[0]) // 2
    shadow(draw, (tx2, 255), title_str, fnt_big, WARM_WHITE)

    # 奶油色內容面板
    panel_top = 420
    panel_bot = 860
    img = ov_rounded(img, [38, panel_top, SIZE[0]-38, panel_bot], 16, (*CREAM, 228))
    draw = ImageDraw.Draw(img)

    # 面板 header
    hdr = f"| {destination} {topic}懶人包 |"
    bb_h = draw.textbbox((0, 0), hdr, font=fr(30))
    hx = (SIZE[0] - (bb_h[2]-bb_h[0])) // 2
    draw.text((hx, panel_top + 14), hdr, font=fr(30), fill=LIGHT_TXT)
    draw.line([(60, panel_top+54), (SIZE[0]-60, panel_top+54)], fill=(*CREAM_DIM, 255), width=2)

    # 條列 tips（彩色數字 + 文字）
    item_y = panel_top + 66
    fnt_item = fr(36)
    fnt_num  = fb(30)
    ICON_W = 52
    for i, tip in enumerate(tips[:4]):
        # 數字圓點
        draw.ellipse([58, item_y + 4, 58 + 36, item_y + 40], fill=color)
        num_bb = draw.textbbox((0,0), str(i+1), font=fnt_num)
        nx = 58 + (36 - (num_bb[2]-num_bb[0])) // 2
        draw.text((nx, item_y + 6), str(i+1), font=fnt_num, fill=WARM_WHITE)

        lines = wrap_text(tip, fnt_item, 860, draw)
        for j, line in enumerate(lines[:2]):
            draw.text((58 + ICON_W, item_y + j * 46), line, font=fnt_item, fill=DARK_TXT)
        item_y += max(len(lines[:2]), 1) * 46 + 16
        if item_y > panel_bot - 60:
            break

    # 底部照片條
    img = build_photo_strip(destination, [destination, topic, f"{destination}{topic}"], 870, img)

    # 互動 + footer
    img = ov_rect(img, [0, 1010, SIZE[0], 1056], (28, 18, 10, 185))
    draw = ImageDraw.Draw(img)
    eng = "按讚  |  追蹤  |  留言城市名取得攻略"
    bb_e = draw.textbbox((0, 0), eng, font=fr(27))
    ex = (SIZE[0] - (bb_e[2]-bb_e[0])) // 2
    draw.text((ex, 1022), eng, font=fr(27), fill=(220, 200, 175))

    img = ov_rect(img, [0, 1056, SIZE[0], SIZE[1]], (15, 9, 4, 210))
    draw = ImageDraw.Draw(img)
    draw.text((52, 1063), "@taiwan.travel.deals", font=fr(27), fill=LIGHT_TXT)
    draw.text((SIZE[0]-200, 1063), "主頁連結 ▶", font=fr(27), fill=(*WARM_GOLD, 220))

    return img


def generate_lazy_guide(destination: str) -> tuple:
    """生成懶人包輪播（7 張）+ caption"""
    print(f"[懶人包] 用 Claude 生成 {destination} 內容...")
    data = _claude_generate(destination)

    cards = [_draw_cover(destination)]
    for topic in ["機票", "住宿", "交通", "美食", "eSIM", "注意事項"]:
        tips = data.get(topic, [f"{topic}資訊整理中...", "敬請期待"] * 2)
        print(f"  生成 {topic} 卡...")
        cards.append(_draw_topic_card(destination, topic, tips))

    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"
    caption = f"""🧳 {destination}旅遊懶人包 一篇搞定！

機票 ✈️ 住宿 🏨 交通 🚌 美食 🍜 eSIM 📶 注意事項 ⚠️
出發前這篇先收藏！

🔗 機票比價 / Klook / KKday 優惠連結全在 👇
{linkinbio}

❤️ 按讚讓更多人看到這篇攻略
🔔 追蹤 @taiwan.travel.deals 不錯過最新優惠
💬 留言「{destination}」幫你整理完整行程

#{destination}旅遊 #{destination}懶人包 #{destination}攻略 #台灣旅遊 #旅遊攻略 #旅遊省錢 #懶人包"""

    return cards, caption
