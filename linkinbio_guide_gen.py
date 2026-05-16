"""
主頁連結懶人包輪播圖生成模組（泰嗨金色風格）
每週一發：教粉絲如何使用主頁連結找到最便宜的旅遊優惠
封面 + 6 個功能說明卡，共 7 張
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

LINKINBIO = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"

# 6 個功能區塊（固定）
SECTIONS = [
    {
        "key":    "flights",
        "title":  "機票比價",
        "emoji":  "✈️",
        "en":     "FLIGHT DEALS",
        "bg":     "airplane boarding gate departure flight",
        "strip1": "airplane window seat clouds sky",
        "strip2": "airport departure board schedule",
    },
    {
        "key":    "klook",
        "title":  "Klook 優惠",
        "emoji":  "🎫",
        "en":     "KLOOK DEALS",
        "bg":     "theme park attraction ticket fun",
        "strip1": "travel experience activity adventure",
        "strip2": "tourist attraction landmark sightseeing",
    },
    {
        "key":    "kkday",
        "title":  "KKday 行程",
        "emoji":  "🗺️",
        "en":     "KKDAY TOURS",
        "bg":     "tour group travel guide map",
        "strip1": "group travel tour bus scenic",
        "strip2": "local experience culture food market",
    },
    {
        "key":    "insurance",
        "title":  "旅遊保險",
        "emoji":  "🛡️",
        "en":     "TRAVEL INSURANCE",
        "bg":     "travel insurance document passport safety",
        "strip1": "travel safety protect document",
        "strip2": "health medical travel emergency",
    },
    {
        "key":    "esim",
        "title":  "eSIM 上網",
        "emoji":  "📶",
        "en":     "eSIM / DATA",
        "bg":     "smartphone travel roaming data network",
        "strip1": "mobile phone navigation map travel",
        "strip2": "sim card digital tech travel",
    },
    {
        "key":    "latest",
        "title":  "最新特價",
        "emoji":  "🔥",
        "en":     "HOT DEALS",
        "bg":     "sale discount deal shopping travel",
        "strip1": "travel deal cheap flight discount",
        "strip2": "hotel deal booking online sale",
    },
]


# ── 漸層 ──────────────────────────────────────────────────────────────────────

def _gradient(img, top_s=155, bot_s=195):
    w, h = img.size
    rgba = img.convert("RGBA")
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(185):
        a = int(top_s * (1 - y / 185) ** 0.7)
        d.line([(0, y), (w-1, y)], fill=(0, 0, 0, a))
    for y in range(700, h):
        a = int(bot_s * ((y-700) / (h-700)) ** 0.5)
        d.line([(0, y), (w-1, y)], fill=(0, 0, 0, a))
    return Image.alpha_composite(rgba, ov).convert("RGB")


# ── 照片條（2 張去重）────────────────────────────────────────────────────────

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
    total = pw * len(photos) + gap * (len(photos) - 1)
    sx = (SIZE[0] - total) // 2
    for i, ph in enumerate(photos):
        img.paste(ph.resize((pw, ph_h), Image.LANCZOS), (sx + i * (pw + gap), strip_y))
    return img


# ── 頁腳 ──────────────────────────────────────────────────────────────────────

def _footer(img):
    w, h = SIZE
    img = ov_rect(img, [0, 950, w, 1010], (28, 18, 10, 185))
    draw = ImageDraw.Draw(img)
    eng = "按讚  |  追蹤  |  點主頁連結找優惠"
    bb = draw.textbbox((0, 0), eng, font=fr(27))
    draw.text(((w - (bb[2]-bb[0])) // 2, 963), eng, font=fr(27), fill=(220, 200, 175))
    img = ov_rect(img, [0, 1010, w, h], (15, 9, 4, 220))
    draw = ImageDraw.Draw(img)
    draw.text((52, 1020), "@taiwan.travel.deals", font=fr(27), fill=LIGHT_TXT)
    draw.text((w-200, 1020), "主頁連結 >>", font=fr(27), fill=(*GOLD, 220))
    return img


# ── Claude 生成各區塊說明文字 ─────────────────────────────────────────────────

def _claude_generate() -> dict:
    """為 6 個功能區塊各生成 4 條說明（每週不同角度）"""
    client = anthropic.Anthropic()
    prompt = f"""你是台灣旅遊 IG 帳號「@taiwan.travel.deals」的小編，主頁連結是一個旅遊優惠整合頁面，包含：
1. 機票比價工具（各大航空最低票價比較）
2. Klook 優惠（日韓泰等亞洲行程、票券、體驗）
3. KKday 旅遊（台灣人開團、包車、一日遊行程）
4. 旅遊保險比較（富邦、台灣人壽、國泰等方案）
5. eSIM 上網購買（Klook eSIM、Airalo、一嗨等品牌）
6. 最新特價整理（每週更新限時優惠）

請生成一篇貼文懶人包的說明內容，用來告訴粉絲「主頁連結裡面有什麼、怎麼用、為什麼值得點進去」。

JSON 格式，每個區塊 4 條說明（每條最多 22 字，繁體中文，具體有說服力）：
{{
  "flights":   ["說明1", "說明2", "說明3", "說明4"],
  "klook":     ["說明1", "說明2", "說明3", "說明4"],
  "kkday":     ["說明1", "說明2", "說明3", "說明4"],
  "insurance": ["說明1", "說明2", "說明3", "說明4"],
  "esim":      ["說明1", "說明2", "說明3", "說明4"],
  "latest":    ["說明1", "說明2", "說明3", "說明4"]
}}

規則：
- 每條要有吸引力，讓人想點進去
- 可以包含具體數字/省錢幅度/品牌名稱（例如：比官網便宜最多 40%、Klook 限時 85 折）
- 語氣輕鬆，像朋友推薦
- 每週角度不同：這次重點放「為什麼選這個比其他平台好」"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1600,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    return json.loads(match.group()) if match else {}


# ── 封面 ──────────────────────────────────────────────────────────────────────

def _draw_cover(sections: list) -> Image.Image:
    bg = get_travel_photo("travel destination collage world map", "", SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.72)
    img = _gradient(bg, 150, 185)
    draw = ImageDraw.Draw(img)
    w, h = SIZE

    draw.text((48, 36), "@taiwan.travel.deals", font=fr(22), fill=(255, 255, 255, 55))

    # 金色橫幅
    img = ov_rect(img, [0, 95, w, 178], (*GOLD, 245))
    draw = ImageDraw.Draw(img)
    band = "旅遊優惠  全部在這裡"
    bb = draw.textbbox((0, 0), band, font=fb(44))
    draw.text(((w - (bb[2]-bb[0])) // 2, 108), band, font=fb(44), fill=GOLD_DARK)

    # 大標題
    fnt_title = ImageFont.truetype(FONT_KAIU, 88)
    title1 = "機票 保險 行程"
    bb2 = draw.textbbox((0, 0), title1, font=fnt_title)
    tx = (w - (bb2[2]-bb2[0])) // 2
    draw.text((tx+4, 198), title1, font=fnt_title, fill=(0, 0, 0, 160))
    draw.text((tx, 194), title1, font=fnt_title, fill=WHITE)

    fnt_title2 = ImageFont.truetype(FONT_KAIU, 88)
    title2 = "看完省很多"
    bb2b = draw.textbbox((0, 0), title2, font=fnt_title2)
    tx2 = (w - (bb2b[2]-bb2b[0])) // 2
    draw.text((tx2+4, 298), title2, font=fnt_title2, fill=(0, 0, 0, 160))
    draw.text((tx2, 294), title2, font=fnt_title2, fill=(*GOLD,))

    # 副標
    sub = "追蹤後點主頁連結，出國少花冤枉錢"
    bb3 = draw.textbbox((0, 0), sub, font=fb(34))
    draw.text(((w - (bb3[2]-bb3[0])) // 2, 396), sub, font=fb(34), fill=(*GOLD, 230))

    # 6 個功能藥丸格
    cols, cell_w, cell_h, grid_top = 3, (w-80)//3, 106, 428
    fnt_pill = fb(28)
    for idx, sec in enumerate(sections[:6]):
        col, row = idx % cols, idx // cols
        cx = 40 + col * cell_w + cell_w // 2
        cy = grid_top + row * cell_h
        pw_p = cell_w - 20
        px = cx - pw_p // 2
        img = ov_rounded(img, [px, cy, px+pw_p, cy+70], 35, (*GOLD, 225))
        label = f"{sec['emoji']} {sec['title']}"
        with Pilmoji(img) as pj:
            tw, _ = pj.getsize(label, font=fnt_pill)
            pj.text((cx - tw//2, cy+14), label, font=fnt_pill, fill=GOLD_DARK)
        draw = ImageDraw.Draw(img)

    # CTA 按鈕
    cta = "點進去 出國少踩雷 荷包省更多"
    fnt_cta = fb(34)
    with Pilmoji(img) as pj:
        cw, _ = pj.getsize(cta, font=fnt_cta)
    cx0 = (w-cw)//2 - 24
    img = ov_rounded(img, [cx0, 666, cx0+cw+48, 666+58], 29, (*GOLD, 255))
    with Pilmoji(img) as pj:
        pj.text(((w-cw)//2, 677), cta, font=fnt_cta, fill=GOLD_DARK)

    img = _strip(
        "travel deal discount booking online",
        "flight hotel comparison website",
        760, img
    )
    return _footer(img)


# ── 功能說明卡 ────────────────────────────────────────────────────────────────

def _draw_section_card(sec: dict, tips: list) -> Image.Image:
    bg = get_travel_photo(sec["bg"], "", SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.70)
    img = _gradient(bg, 165, 200)
    draw = ImageDraw.Draw(img)
    w, h = SIZE

    draw.text((48, 36), "@taiwan.travel.deals", font=fr(22), fill=(255, 255, 255, 55))

    # EN 分類
    fnt_en = fb(62)
    bb = draw.textbbox((0, 0), sec["en"], font=fnt_en)
    tx_en = (w - (bb[2]-bb[0])) // 2
    draw.text((tx_en+3, 83), sec["en"], font=fnt_en, fill=(0, 0, 0, 140))
    draw.text((tx_en, 80), sec["en"], font=fnt_en, fill=(*GOLD,))

    # 主標題（標楷體）
    title_str = f"{sec['emoji']} {sec['title']}"
    fnt_zh = ImageFont.truetype(FONT_KAIU, 92)
    with Pilmoji(img) as pj:
        tw, _ = pj.getsize(title_str, font=fnt_zh)
    tx_zh = (w - tw) // 2
    with Pilmoji(img) as pj:
        pj.text((tx_zh+4, 164), title_str, font=fnt_zh, fill=(0, 0, 0))
    with Pilmoji(img) as pj:
        pj.text((tx_zh, 160), title_str, font=fnt_zh, fill=WHITE)
    draw = ImageDraw.Draw(img)

    # 金色標籤
    pill_text = "主頁連結  點進去就有"
    fnt_pill = fb(32)
    bb_p = draw.textbbox((0, 0), pill_text, font=fnt_pill)
    pw_p = bb_p[2]-bb_p[0]
    px_p = (w-pw_p)//2 - 22
    img = ov_rounded(img, [px_p, 332, px_p+pw_p+44, 332+50], 25, (*GOLD, 240))
    draw = ImageDraw.Draw(img)
    bb_p2 = draw.textbbox((0, 0), pill_text, font=fnt_pill)
    draw.text(((w-(bb_p2[2]-bb_p2[0]))//2, 342), pill_text, font=fnt_pill, fill=GOLD_DARK)

    # 說明條列（自適應字體）
    max_len = max((len(t) for t in tips[:4]), default=0)
    if max_len > 26:
        fnt_tip, line_h = fr(33), 44
    elif max_len > 20:
        fnt_tip, line_h = fr(36), 48
    else:
        fnt_tip, line_h = fr(38), 50

    item_y = 408
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

    img = _strip(sec["strip1"], sec["strip2"], 760, img)
    return _footer(img)


# ── 主入口 ────────────────────────────────────────────────────────────────────

def generate_linkinbio_guide() -> tuple:
    """生成主頁連結使用指南輪播（7 張）+ caption"""
    print("[主頁連結懶人包] 用 Claude 生成本週說明內容...")
    data = _claude_generate()

    cards = [_draw_cover(SECTIONS)]
    for sec in SECTIONS:
        tips = data.get(sec["key"], [
            f"點主頁連結直接查看{sec['title']}",
            "每週更新最新優惠",
            "比自己找省時又省錢",
            "台灣人整理，中文介面好懂",
        ])
        print(f"  生成「{sec['title']}」卡...")
        cards.append(_draw_section_card(sec, tips))

    caption = f"""🔗 主頁連結裡面到底有什麼？這篇告訴你！

很多人追蹤了但不知道連結可以幹嘛
其實裡面整合了出國最常用的 6 種工具 👆

✈️ 機票比價｜🎫 Klook 優惠｜🗺️ KKday 行程
🛡️ 旅遊保險｜📶 eSIM 上網｜🔥 本週特價

全部都在這個連結：
{LINKINBIO}

❤️ 覺得實用請按讚讓更多人看到
🔔 追蹤 @taiwan.travel.deals 每週更新優惠
💬 留言告訴我你最常用哪個功能？

#旅遊優惠 #機票比價 #Klook #KKday #旅遊保險 #eSIM #台灣旅遊 #出國攻略 #旅遊省錢 #懶人包"""

    return cards, caption
