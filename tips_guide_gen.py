"""
出國注意事項懶人包輪播圖生成模組（泰嗨金色風格）
封面 + 6 個子主題卡，共 7 張
星期二、四、六使用
"""
import os
import json
import re
import anthropic
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pilmoji import Pilmoji
from dotenv import load_dotenv

from guide_gen import (
    ov_rounded, ov_rect, fb, fr,
    wrap_text, LIGHT_TXT, SIZE,
)
from pexels import search_photos, download_image, get_travel_photo

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from font_paths import FONT_KAIU

GOLD      = (245, 197, 0)
GOLD_DARK = (30, 20, 5)
WHITE     = (255, 255, 255)

# 每個主題的封面背景搜尋詞
TOPIC_BG = {
    "旅遊保險":         "travel insurance document passport",
    "航空公司怎麼選":   "airplane boarding flight seat",
    "國際駕照申請與租車": "car rental road trip driving",
    "搭廉航注意事項":   "budget airline terminal airport",
    "行李打包與托運規定": "travel luggage suitcase packing",
    "海外信用卡與換匯攻略": "credit card money exchange travel",
    "eSIM 選購完整攻略": "smartphone sim card travel roaming",
    "機場快速通關技巧": "airport security check passport",
    "海外緊急應變指南": "emergency travel safety help",
    "出國前必做準備清單": "travel checklist preparation map",
    "海外醫療與看病流程": "hospital medical travel health",
    "訂機票省錢完整攻略": "airplane ticket booking cheap flight",
    "訂旅館比價攻略":   "hotel booking online comparison",
    "出國必備旅遊 App": "smartphone travel app navigation",
    "護照 簽證 申請流程": "passport visa document official",
    "海外行動上網完整攻略": "mobile internet roaming travel data",
    "旅遊詐騙常見手法防範": "travel scam tourist warning caution",
    "台灣出發最划算機場交通": "airport bus train transport arrival",
}


# ── 漸層 ──────────────────────────────────────────────────────────────────────

def _gradient(img, top_s=155, bot_s=195):
    w, h = img.size
    rgba = img.convert("RGBA")
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(180):
        a = int(top_s * (1 - y / 180) ** 0.7)
        d.line([(0, y), (w-1, y)], fill=(0, 0, 0, a))
    for y in range(700, h):
        a = int(bot_s * ((y-700) / (h-700)) ** 0.5)
        d.line([(0, y), (w-1, y)], fill=(0, 0, 0, a))
    return Image.alpha_composite(rgba, ov).convert("RGB")


# ── 去重照片條（2 張大圖）────────────────────────────────────────────────────

def _strip(q1, q2, strip_y, img):
    used = set()
    photos = []
    for q in [q1, q2]:
        for url in search_photos(q, count=8, orientation="landscape"):
            if url not in used:
                used.add(url)
                photos.append(download_image(url, (500, 210)))
                break
    if not photos:
        return img
    pw, ph_h, gap = 500, 210, 40
    total = pw * len(photos) + gap * (len(photos)-1)
    sx = (SIZE[0] - total) // 2
    for i, ph in enumerate(photos):
        img.paste(ph.resize((pw, ph_h), Image.LANCZOS), (sx + i*(pw+gap), strip_y))
    return img


# ── 頁腳 ──────────────────────────────────────────────────────────────────────

def _footer(img):
    w, h = SIZE
    img = ov_rect(img, [0, 950, w, 1010], (28, 18, 10, 185))
    draw = ImageDraw.Draw(img)
    eng = "按讚  |  追蹤  |  分享給也要出國的朋友"
    bb = draw.textbbox((0, 0), eng, font=fr(27))
    draw.text(((w - (bb[2]-bb[0])) // 2, 963), eng, font=fr(27), fill=(220, 200, 175))
    img = ov_rect(img, [0, 1010, w, h], (15, 9, 4, 220))
    draw = ImageDraw.Draw(img)
    draw.text((52, 1020), "@taiwan.travel.deals", font=fr(27), fill=LIGHT_TXT)
    draw.text((w-200, 1020), "主頁連結 >>", font=fr(27), fill=(*GOLD, 220))
    return img


# ── Claude 生成內容 ───────────────────────────────────────────────────────────

def _claude_generate(topic: str) -> dict:
    """生成 6 個子主題，每個 4 條建議"""
    client = anthropic.Anthropic()
    prompt = f"""你是專業旅遊達人，請用你所有知識為「{topic}」生成出國注意事項懶人包。

請以 JSON 格式回應，包含：
1. "subtopics"：6 個子主題名稱（4字以內，用 emoji 開頭，例如「💡 常見問題」）
2. 每個子主題的 4 條建議（每條最多 24 字）

格式：
{{
  "subtopics": ["📋 子主題1", "💰 子主題2", "⚠️ 子主題3", "✅ 子主題4", "📱 子主題5", "🔍 子主題6"],
  "📋 子主題1": ["建議1", "建議2", "建議3", "建議4"],
  "💰 子主題2": ["建議1", "建議2", "建議3", "建議4"],
  ...（其餘類推）
}}

規則：
- 台灣人出國視角，繁體中文
- 內容必須具體：有品牌名稱、數字、金額、網站、App 名稱更好（例如：Wise 換匯手續費 0.5%、Airalo eSIM 7天$15美金、旅平險推薦台灣人壽/富邦）
- 針對「{topic}」這個主題，6 個子主題要涵蓋不同面向（前置準備、實際使用、省錢技巧、常見錯誤等）
- 每條建議簡短有力，讓人看了馬上知道要怎麼做
- 用你的知識補充台灣人容易忽略的細節"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1800,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    return json.loads(match.group()) if match else {}


# ── 封面 ──────────────────────────────────────────────────────────────────────

def _draw_cover(topic: str, subtopics: list) -> Image.Image:
    bg_q = TOPIC_BG.get(topic, f"travel {topic} guide")
    bg = get_travel_photo(bg_q, "", SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.78)
    img = _gradient(bg, 150, 180)
    draw = ImageDraw.Draw(img)
    w, h = SIZE

    draw.text((48, 36), "@taiwan.travel.deals", font=fr(22), fill=(255, 255, 255, 55))

    # 金色橫幅
    img = ov_rect(img, [0, 95, w, 178], (*GOLD, 245))
    draw = ImageDraw.Draw(img)
    band = "出國必知  一篇搞定"
    bb = draw.textbbox((0, 0), band, font=fb(44))
    draw.text(((w - (bb[2]-bb[0])) // 2, 108), band, font=fb(44), fill=GOLD_DARK)

    # 大標題（標楷體）
    fnt_title = ImageFont.truetype(FONT_KAIU, 100 if len(topic) > 6 else 115)
    draw = ImageDraw.Draw(img)
    bb2 = draw.textbbox((0, 0), topic, font=fnt_title)
    tx = (w - (bb2[2]-bb2[0])) // 2
    draw.text((tx+4, 196), topic, font=fnt_title, fill=(0, 0, 0, 160))
    draw.text((tx, 192), topic, font=fnt_title, fill=WHITE)

    # 副標題
    sub = "出發前這些你一定要知道"
    bb3 = draw.textbbox((0, 0), sub, font=fb(36))
    draw.text(((w - (bb3[2]-bb3[0])) // 2, 358), sub, font=fb(36), fill=(*GOLD, 230))

    # 子主題藥丸格 2x3
    cols, cell_w, cell_h, grid_top = 3, (w-80)//3, 106, 426
    fnt_pill = fb(28)
    for idx, st in enumerate(subtopics[:6]):
        col, row = idx % cols, idx // cols
        cx = 40 + col*cell_w + cell_w//2
        cy = grid_top + row*cell_h
        pw = cell_w - 20
        px = cx - pw//2
        img = ov_rounded(img, [px, cy, px+pw, cy+70], 35, (*GOLD, 225))
        with Pilmoji(img) as pj:
            tw, _ = pj.getsize(st, font=fnt_pill)
            pj.text((cx-tw//2, cy+14), st, font=fnt_pill, fill=GOLD_DARK)
        draw = ImageDraw.Draw(img)

    # CTA
    cta = "先收藏 ✨  出發前看這篇就夠了"
    fnt_cta = fb(36)
    with Pilmoji(img) as pj:
        cw, _ = pj.getsize(cta, font=fnt_cta)
    cx0 = (w-cw)//2 - 24
    img = ov_rounded(img, [cx0, 664, cx0+cw+48, 664+58], 29, (*GOLD, 255))
    with Pilmoji(img) as pj:
        pj.text(((w-cw)//2, 675), cta, font=fnt_cta, fill=GOLD_DARK)

    img = _strip(f"{topic} travel", "travel guide preparation", 758, img)
    return _footer(img)


# ── 子主題卡 ──────────────────────────────────────────────────────────────────

def _draw_subtopic_card(topic: str, subtopic: str, tips: list) -> Image.Image:
    bg_q = TOPIC_BG.get(topic, "travel guide tips")
    bg = get_travel_photo(bg_q, "", SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.72)
    img = _gradient(bg, 165, 200)
    draw = ImageDraw.Draw(img)
    w, h = SIZE

    draw.text((48, 36), "@taiwan.travel.deals", font=fr(22), fill=(255, 255, 255, 55))

    # EN 分類標（移除 emoji 後取英文）
    en_map = {
        "旅遊保險": "INSURANCE", "航空公司怎麼選": "AIRLINES",
        "國際駕照申請與租車": "DRIVING", "搭廉航注意事項": "LOW COST",
        "行李打包與托運規定": "LUGGAGE", "海外信用卡與換匯攻略": "MONEY",
        "eSIM 選購完整攻略": "eSIM", "機場快速通關技巧": "AIRPORT",
        "海外緊急應變指南": "EMERGENCY", "出國前必做準備清單": "CHECKLIST",
        "海外醫療與看病流程": "MEDICAL", "訂機票省錢完整攻略": "FLIGHTS",
        "訂旅館比價攻略": "HOTEL", "出國必備旅遊 App": "TRAVEL APP",
        "護照 簽證 申請流程": "VISA", "海外行動上網完整攻略": "DATA",
        "旅遊詐騙常見手法防範": "SCAM ALERT", "台灣出發最划算機場交通": "AIRPORT BUS",
    }
    en = en_map.get(topic, "TRAVEL TIPS")
    fnt_en = fb(62)
    bb = draw.textbbox((0, 0), en, font=fnt_en)
    tx_en = (w - (bb[2]-bb[0])) // 2
    draw.text((tx_en+3, 83), en, font=fnt_en, fill=(0, 0, 0, 140))
    draw.text((tx_en, 80), en, font=fnt_en, fill=(*GOLD,))

    # 子主題名（標楷體白色）
    # 去掉開頭 emoji（Unicode 可能 2 個字元）
    clean = subtopic.strip()
    fnt_zh = ImageFont.truetype(FONT_KAIU, 88)
    with Pilmoji(img) as pj:
        tw, _ = pj.getsize(clean, font=fnt_zh)
    tx_zh = (w - tw) // 2
    with Pilmoji(img) as pj:
        pj.text((tx_zh+4, 164), clean, font=fnt_zh, fill=(0, 0, 0))
    with Pilmoji(img) as pj:
        pj.text((tx_zh, 160), clean, font=fnt_zh, fill=WHITE)
    draw = ImageDraw.Draw(img)

    # 金色標籤
    pill_text = f"{topic} 攻略"
    fnt_pill = fb(32)
    bb_p = draw.textbbox((0, 0), pill_text, font=fnt_pill)
    pw_p = bb_p[2]-bb_p[0]
    px_p = (w-pw_p)//2 - 22
    img = ov_rounded(img, [px_p, 330, px_p+pw_p+44, 330+50], 25, (*GOLD, 240))
    draw = ImageDraw.Draw(img)
    bb_p2 = draw.textbbox((0, 0), pill_text, font=fnt_pill)
    draw.text(((w-(bb_p2[2]-bb_p2[0]))//2, 340), pill_text, font=fnt_pill, fill=GOLD_DARK)

    # tips 列表（自適應字體大小）
    max_len = max((len(t) for t in tips[:4]), default=0)
    if max_len > 26:
        fnt_tip, line_h = fr(33), 44
    elif max_len > 20:
        fnt_tip, line_h = fr(36), 48
    else:
        fnt_tip, line_h = fr(38), 50

    item_y = 405
    fnt_num = fb(28)
    CR = 20
    TIP_X = 58 + CR*2 + 18
    for i, tip in enumerate(tips[:4]):
        cx_c = 58 + CR
        img = ov_rounded(img, [cx_c-CR, item_y+4, cx_c+CR, item_y+4+CR*2], CR, (*GOLD, 255))
        draw = ImageDraw.Draw(img)
        nb = draw.textbbox((0, 0), str(i+1), font=fnt_num)
        draw.text((cx_c-(nb[2]-nb[0])//2, item_y+5), str(i+1), font=fnt_num, fill=GOLD_DARK)
        lines = wrap_text(tip, fnt_tip, w-TIP_X-40, draw)
        for j, line in enumerate(lines[:2]):
            draw.text((TIP_X+2, item_y+j*line_h+2), line, font=fnt_tip, fill=(0, 0, 0, 130))
            draw.text((TIP_X, item_y+j*line_h), line, font=fnt_tip, fill=WHITE)
        item_y += max(len(lines[:2]), 1)*line_h + 16
        if item_y > 810:
            break

    img = _strip(f"{topic} tips", f"{en.lower()} travel guide", 758, img)
    return _footer(img)


# ── 主入口 ────────────────────────────────────────────────────────────────────

def generate_tips_guide(topic: str) -> tuple:
    """生成出國注意事項懶人包（7 張）+ caption"""
    print(f"[注意事項懶人包] 用 Claude 生成「{topic}」內容...")
    data = _claude_generate(topic)
    subtopics = data.get("subtopics", [
        "📋 基本須知", "💰 費用預算", "⚠️ 常見錯誤",
        "✅ 必做清單", "📱 實用工具", "🔍 常見問題"
    ])

    cards = [_draw_cover(topic, subtopics)]
    for st in subtopics[:6]:
        tips = data.get(st, ["詳細資訊整理中...", "敬請期待"] * 2)
        print(f"  生成「{st}」卡...")
        cards.append(_draw_subtopic_card(topic, st, tips))

    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"
    caption = f"""✈️ {topic} 出國必知懶人包！

這些事很多人都不知道，出發前一定要看 👆
省錢省力省麻煩，一篇搞定！

🔗 機票比價 / 保險 / 旅遊優惠連結全在 👇
{linkinbio}

❤️ 按讚讓更多人看到這篇
🔔 追蹤 @taiwan.travel.deals 不錯過出國攻略
💬 留言告訴我你最想知道哪個主題

#{topic.replace(" ", "")} #出國攻略 #旅遊必知 #台灣旅遊 #出國注意 #旅遊省錢 #懶人包"""

    return cards, caption
