"""
旅遊攻略輪播圖生成模組 v4
風格參考：萊旅遊 @liketravel_official
暖色調 + 奶油面板 + emoji 圖示 + Polaroid 底部
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from pilmoji import Pilmoji
from pexels import get_travel_photo, search_photos, download_image

FONT_BOLD  = "C:/Windows/Fonts/msjhbd.ttc"
FONT_REG   = "C:/Windows/Fonts/msjh.ttc"
FONT_EMOJI = "C:/Windows/Fonts/seguiemj.ttf"
SIZE = (1080, 1080)

# ── 暖色調色盤 ────────────────────────────────────────────────────────────────
WARM_ORANGE = (210, 118, 38)
WARM_GOLD   = (192, 152, 72)
CREAM       = (248, 243, 232)
CREAM_DIM   = (235, 228, 214)
DARK_TXT    = (42, 28, 16)
MID_TXT     = (105, 88, 70)
LIGHT_TXT   = (162, 145, 124)
WARM_WHITE  = (255, 252, 248)
RED_TAG     = (195, 72, 58)
TEAL_TAG    = (62, 148, 142)
DEEP_BROWN  = (28, 18, 10)

DAY_COLORS  = [
    (210, 118, 38),   # 橙
    (62, 148, 142),   # 青
    (168, 88, 130),   # 玫瑰
    (88, 140, 80),    # 綠
    (138, 100, 178),  # 紫
]

# ── 關鍵字自動選 emoji 圖示 ───────────────────────────────────────────────────
_ICON_MAP = [
    ("🌅", ["夕陽", "日落", "夜景", "夜晚", "日出", "黃昏", "黎明"]),
    ("🏔", ["山", "富士山", "全景", "景觀", "展望", "高空", "頂樓", "360"]),
    ("🍜", ["拉麵", "麵", "湯", "火鍋", "鍋"]),
    ("🍣", ["壽司", "生魚", "海鮮", "魚", "蟹", "蝦", "刺身", "海膽", "鮪魚", "鰻魚"]),
    ("🍳", ["玉子", "蛋", "厚蛋", "煎蛋"]),
    ("🥩", ["燒肉", "牛肉", "和牛", "豬", "排", "烤肉"]),
    ("🍱", ["便當", "定食", "懷石", "料理", "美食", "在地", "串燒", "居酒屋"]),
    ("🍦", ["冰淇淋", "霜淇淋", "甜點", "甜食", "布丁", "抹茶"]),
    ("🎨", ["藝術", "展覽", "打卡", "裝置", "拍照", "出片", "攝影"]),
    ("🌊", ["沙灘", "海灘", "浮潛", "潛水", "游泳"]),
    ("🌸", ["公園", "花", "自然", "綠地", "森林", "植物", "賞花"]),
    ("🎭", ["文化", "歷史", "廟", "神社", "古蹟", "博物館", "宮"]),
    ("💰", ["省錢", "便宜", "優惠", "折扣", "票價", "費用", "CP", "5折", "免費"]),
    ("🚇", ["地鐵", "捷運", "鐵路", "IC卡", "交通", "搭乘", "路線", "巴士", "JR"]),
    ("🏨", ["飯店", "住宿", "酒店", "民宿"]),
    ("🛍", ["購物", "超市", "商店", "伴手禮", "百貨"]),
    ("⚠️", ["注意", "避雷", "踩坑", "警告", "小心"]),
    ("💡", ["提示", "技巧", "建議", "小秘訣"]),
    ("📍", ["地址", "位置", "地點", "景點", "必去", "必訪"]),
]

def auto_icon(text: str) -> str:
    """根據文字內容自動選擇對應 emoji"""
    for icon, keywords in _ICON_MAP:
        if any(kw in text for kw in keywords):
            return icon
    return "🔸"  # 小橙鑽，Segoe UI Emoji 支援


def fb(size): return ImageFont.truetype(FONT_BOLD, size)
def fr(size): return ImageFont.truetype(FONT_REG, size)
def fe(size): return ImageFont.truetype(FONT_EMOJI, size)


def wrap_text(text, font, max_w, draw):
    lines, cur = [], ""
    for ch in text:
        test = cur + ch
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def shadow(draw, xy, text, fnt, color=WARM_WHITE):
    x, y = xy
    draw.text((x+2, y+2), text, font=fnt, fill=(0, 0, 0, 120))
    draw.text(xy, text, font=fnt, fill=color)


def center_x(draw, y, text, fnt, color=WARM_WHITE):
    bb = draw.textbbox((0, 0), text, font=fnt)
    x = (SIZE[0] - (bb[2] - bb[0])) // 2
    shadow(draw, (x, y), text, fnt, color)
    return bb[3] - bb[1]


def ov_rect(img, box, fill_rgba):
    rgba = img.convert("RGBA")
    ov = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle(box, fill=fill_rgba)
    return Image.alpha_composite(rgba, ov).convert("RGB")


def ov_rounded(img, box, radius, fill_rgba):
    rgba = img.convert("RGBA")
    ov = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(box, radius=radius, fill=fill_rgba)
    return Image.alpha_composite(rgba, ov).convert("RGB")


def warm_overlay(img, strength=0.55):
    """暖色漸層疊加 + 下半部加深"""
    rgba = img.convert("RGBA")
    ov = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(SIZE[1]):
        t = (y / SIZE[1]) ** 1.8
        base_a = int(strength * 255 * t)
        d.line([(0, y), (SIZE[0], y)], fill=(20, 12, 5, base_a))
    return Image.alpha_composite(rgba, ov).convert("RGB")


def draw_day_circle(img, cx, cy, day_num, color):
    """D1/D2 彩色圓圈"""
    r = 24
    img = ov_rounded(img, [cx - r, cy - r, cx + r, cy + r], r, (*color, 235))
    draw = ImageDraw.Draw(img)
    label = f"D{day_num}"
    fnt = fb(22)
    bb = draw.textbbox((0, 0), label, font=fnt)
    tx = cx - (bb[2] - bb[0]) // 2
    ty = cy - (bb[3] - bb[1]) // 2
    draw.text((tx, ty), label, font=fnt, fill=WARM_WHITE)
    return img


def make_polaroid(photo: Image.Image, label: str, w=320, h=200) -> Image.Image:
    """Polaroid 風格小照片"""
    border = 10
    label_h = 32
    total_h = h + border * 2 + label_h
    card = Image.new("RGB", (w, total_h), WARM_WHITE)

    # 縮放照片
    ph = photo.resize((w - border * 2, h), Image.LANCZOS)
    card.paste(ph, (border, border))

    # 底部標籤
    d = ImageDraw.Draw(card)
    fnt = fr(22)
    bb = d.textbbox((0, 0), label, font=fnt)
    tx = (w - (bb[2] - bb[0])) // 2
    d.text((tx, h + border + 5), label, font=fnt, fill=MID_TXT)

    # 輕微陰影（整體降暗邊緣）
    enhancer = ImageEnhance.Brightness(card)
    return card


def build_photo_strip(destination: str, labels: list, strip_y: int,
                       img: Image.Image) -> Image.Image:
    """底部三張 Polaroid 照片橫排"""
    strip_photos = []
    for lbl in labels[:3]:
        q = f"{destination} {lbl}"
        urls = search_photos(q, count=1)
        ph = download_image(urls[0], (320, 200)) if urls else Image.new("RGB", (320, 200), CREAM_DIM)
        strip_photos.append((ph, lbl))

    pw, ph_h = 320, 200
    gap = 20
    total_w = pw * 3 + gap * 2
    start_x = (SIZE[0] - total_w) // 2

    for i, (ph, lbl) in enumerate(strip_photos):
        px = start_x + i * (pw + gap)
        pol = make_polaroid(ph, lbl, pw, ph_h)
        img.paste(pol, (px, strip_y))

    return img


# ─────────────────────────────────────────────────────────────────────────────
# 主卡片：Power Card（一張搞定）
# ─────────────────────────────────────────────────────────────────────────────

def make_power_card(
    destination: str,
    tag: str,            # 如「必去」「必吃」「激推」
    title: str,          # 大標題（可與 destination 相同或更短）
    subtitle: str,       # 如「5 日 4 夜」「精華行程」
    panel_header: str,   # 面板頂行，如「行程一次看懂」
    items: list,         # D1/D2... 文字 list，最多 5 條
    strip_labels: list,  # 底部 3 張照片的搜尋標籤
    bg_theme: str = "",
    tag_color=None,
) -> Image.Image:
    tag_color = tag_color or WARM_ORANGE

    # ── 背景照片 ──────────────────────────────────────────────────────────────
    bg = get_travel_photo(destination, bg_theme, SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.72)
    img = warm_overlay(bg)

    # ── 城市浮水印（左上，低透明度） ──────────────────────────────────────
    draw = ImageDraw.Draw(img)
    draw.text((52, 38), destination, font=fr(32), fill=(255, 252, 248, 55))

    # ── 標籤 ─────────────────────────────────────────────────────────────────
    fnt_tag = fb(34)
    tag_str = f"  \\ {tag} /  "
    bb = draw.textbbox((0, 0), tag_str, font=fnt_tag)
    tw = bb[2] - bb[0]
    tx = (SIZE[0] - tw) // 2
    img = ov_rounded(img, [tx - 16, 195, tx + tw + 16, 195 + (bb[3]-bb[1]) + 14], 20,
                     (*tag_color, 220))
    draw = ImageDraw.Draw(img)
    draw.text((tx, 202), tag_str, font=fnt_tag, fill=WARM_WHITE)

    # ── 大標題 ────────────────────────────────────────────────────────────────
    fnt_big = fb(120)
    bb2 = draw.textbbox((0, 0), title, font=fnt_big)
    tw2 = bb2[2] - bb2[0]
    tx2 = (SIZE[0] - tw2) // 2
    shadow(draw, (tx2, 258), title, fnt_big, WARM_WHITE)

    # ── 副標（天數） ─────────────────────────────────────────────────────────
    fnt_sub = fb(54)
    bb3 = draw.textbbox((0, 0), subtitle, font=fnt_sub)
    tw3 = bb3[2] - bb3[0]
    tx3 = (SIZE[0] - tw3) // 2
    shadow(draw, (tx3, 400), subtitle, fnt_sub, WARM_WHITE)

    # ── 奶油色內容面板 ────────────────────────────────────────────────────────
    panel_top = 484
    panel_bot = 844
    img = ov_rounded(img, [38, panel_top, SIZE[0] - 38, panel_bot], 16,
                     (*CREAM, 228))

    draw = ImageDraw.Draw(img)

    # 面板 header
    fnt_hdr = fr(30)
    hdr_str = f"| {panel_header} |"
    bb_h = draw.textbbox((0, 0), hdr_str, font=fnt_hdr)
    hx = (SIZE[0] - (bb_h[2] - bb_h[0])) // 2
    draw.text((hx, panel_top + 16), hdr_str, font=fnt_hdr, fill=LIGHT_TXT)

    # 橫分隔線
    line_y = panel_top + 56
    draw.line([(60, line_y), (SIZE[0]-60, line_y)], fill=(*CREAM_DIM, 255), width=2)

    # 條列項目：彩色 emoji 圖示 + 文字，不使用任何框框
    item_y = panel_top + 68
    fnt_item = fr(34)
    fnt_icon = fe(36)   # Segoe UI Emoji font for proper color emoji rendering
    ICON_W = 52          # fixed icon slot width
    draw = ImageDraw.Draw(img)
    with Pilmoji(img) as pm:
        for i, item in enumerate(items[:5]):
            icon = auto_icon(item)
            pm.text((58, item_y), icon, font=fnt_icon, fill=DARK_TXT)
            lines = wrap_text(item, fnt_item, 900, draw)
            for j, line in enumerate(lines):
                draw.text((58 + ICON_W, item_y + 4 + j * 44), line, font=fnt_item, fill=DARK_TXT)
            item_y += max(len(lines), 1) * 44 + 12

    # ── 底部 Polaroid 照片橫排 ────────────────────────────────────────────────
    strip_y = 856
    if strip_labels:
        img = build_photo_strip(destination, strip_labels[:3], strip_y, img)

    # ── 互動提示條 ───────────────────────────────────────────────────────────
    img = ov_rect(img, [0, 1010, SIZE[0], 1056], (28, 18, 10, 185))
    draw = ImageDraw.Draw(img)
    eng = "按讚  |  追蹤  |  留言城市名取得攻略"
    bb_e = draw.textbbox((0, 0), eng, font=fr(27))
    ex = (SIZE[0] - (bb_e[2]-bb_e[0])) // 2
    draw.text((ex, 1022), eng, font=fr(27), fill=(220, 200, 175))

    # ── 帳號 footer ───────────────────────────────────────────────────────────
    img = ov_rect(img, [0, 1056, SIZE[0], SIZE[1]], (15, 9, 4, 210))
    draw = ImageDraw.Draw(img)
    draw.text((52, 1063), "@taiwan.travel.deals", font=fr(27), fill=LIGHT_TXT)
    draw.text((SIZE[0]-200, 1063), "主頁連結 ▶", font=fr(27), fill=(*WARM_GOLD, 220))

    return img


# ─────────────────────────────────────────────────────────────────────────────
# 景點/美食單卡（簡潔版，1-2 張）
# ─────────────────────────────────────────────────────────────────────────────

def make_spot_card(
    spot_name: str,
    location: str,
    tag: str,
    highlights: list,      # 3-5 條重點
    transport_line: str,   # 單行交通摘要
    strip_labels: list,
    tag_color=None,
) -> Image.Image:
    tag_color = tag_color or RED_TAG

    bg = get_travel_photo(f"{location} {spot_name}", "", SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.68)
    img = warm_overlay(bg)

    draw = ImageDraw.Draw(img)
    draw.text((52, 38), location, font=fr(32), fill=(255, 252, 248, 55))

    # 標籤
    fnt_tag = fb(34)
    tag_str = f"  \\ {tag} /  "
    bb = draw.textbbox((0, 0), tag_str, font=fnt_tag)
    tw = bb[2] - bb[0]
    tx = (SIZE[0] - tw) // 2
    img = ov_rounded(img, [tx - 16, 168, tx + tw + 16, 168 + (bb[3]-bb[1]) + 14],
                     20, (*tag_color, 215))
    draw = ImageDraw.Draw(img)
    draw.text((tx, 175), tag_str, font=fnt_tag, fill=WARM_WHITE)

    # 景點名
    fnt_big = fb(110)
    bb2 = draw.textbbox((0, 0), spot_name, font=fnt_big)
    tw2 = bb2[2] - bb2[0]
    if tw2 > 960:
        fnt_big = fb(80)
        bb2 = draw.textbbox((0, 0), spot_name, font=fnt_big)
        tw2 = bb2[2] - bb2[0]
    shadow(draw, ((SIZE[0]-tw2)//2, 228), spot_name, fnt_big, WARM_WHITE)

    # 奶油面板
    panel_top = 398
    panel_bot = 838
    img = ov_rounded(img, [38, panel_top, SIZE[0]-38, panel_bot], 16, (*CREAM, 225))
    draw = ImageDraw.Draw(img)

    draw.line([(60, panel_top+44), (SIZE[0]-60, panel_top+44)], fill=(*CREAM_DIM, 255), width=2)

    y = panel_top + 54
    fnt_item = fr(36)
    fnt_icon = fe(36)   # Segoe UI Emoji font
    ICON_W = 52
    draw = ImageDraw.Draw(img)
    with Pilmoji(img) as pm:
        for i, h in enumerate(highlights[:5]):
            icon = auto_icon(h)
            pm.text((56, y), icon, font=fnt_icon, fill=DARK_TXT)
            lines = wrap_text(h, fnt_item, 970 - ICON_W, draw)
            for j, line in enumerate(lines):
                draw.text((56 + ICON_W, y + 4 + j * 48), line, font=fnt_item, fill=DARK_TXT)
            y += max(len(lines), 1) * 48 + 12

    # 交通摘要
    if transport_line:
        y = max(y + 12, panel_bot - 80)
        draw = ImageDraw.Draw(img)
        draw.line([(56, y), (SIZE[0]-56, y)], fill=(*CREAM_DIM, 200), width=1)
        draw.text((104, y + 10), transport_line, font=fr(30), fill=MID_TXT)
        with Pilmoji(img) as pm:
            pm.text((60, y + 10), "🚇", font=fe(30), fill=MID_TXT)

    # Polaroid
    if strip_labels:
        img = build_photo_strip(location, strip_labels[:3], 852, img)

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


# ─────────────────────────────────────────────────────────────────────────────
# 外部接口（向下相容）
# ─────────────────────────────────────────────────────────────────────────────

def generate_guide_carousel(destination: str, days: int, subtitle_text: str,
                              sections: list, warnings: list = None) -> list:
    """
    生成旅遊攻略輪播（Power Card 風格）
    sections: [{"title":"...","icon":"...","items":[...],"theme":"..."}, ...]
    """
    cards = []

    # 主攻略卡（含行程）
    itinerary_items = []
    for sec in sections[:5]:
        for it in sec.get("items", [])[:1]:
            text = it if isinstance(it, str) else it.get("title", "")
            itinerary_items.append(f"{sec['icon']} {text}")

    cards.append(make_power_card(
        destination=destination,
        tag=f"{days}天{days-1}夜",
        title=destination,
        subtitle=subtitle_text,
        panel_header="行程一次看懂",
        items=itinerary_items[:5],
        strip_labels=[s.get("theme", destination) for s in sections[:3]],
        bg_theme="scenic landmark",
    ))

    # 各主題內容卡（如美食、省錢等）
    for sec in sections:
        all_items = []
        for it in sec.get("items", []):
            if isinstance(it, str):
                all_items.append(it)
            elif isinstance(it, dict):
                all_items.append(f"{it['title']}：{it['desc']}")

        cards.append(make_power_card(
            destination=destination,
            tag=sec["title"],
            title=destination,
            subtitle=sec["title"],
            panel_header=sec.get("theme", sec["title"]),
            items=all_items[:5],
            strip_labels=[destination, sec.get("theme", ""), destination + " food"],
            bg_theme=sec.get("theme", ""),
            tag_color=TEAL_TAG if "食" in sec["title"] or "吃" in sec["title"] else None,
        ))

    # 避雷卡
    if warnings:
        warn_card = make_power_card(
            destination=destination,
            tag="避雷提醒",
            title="踩坑警告",
            subtitle=f"去 {destination} 前必看",
            panel_header="這幾點一定要注意",
            items=[f"✗  {w}" for w in warnings[:5]],
            strip_labels=[destination] * 3,
            tag_color=RED_TAG,
        )
        cards.append(warn_card)

    return cards


def generate_spot_carousel(spot_name: str, location: str, category: str,
                             highlights: list, transport: dict,
                             hours: str, price: str, address: str, tips: list) -> list:
    """生成景點/美食介紹（1-2 張 Power Card）"""
    transport_summary = ""
    if transport:
        parts = []
        if transport.get("route"):   parts.append(transport["route"])
        if transport.get("station"): parts.append(f"{transport['station']}")
        if transport.get("walk"):    parts.append(transport["walk"])
        transport_summary = "  |  ".join(parts)

    card = make_spot_card(
        spot_name=spot_name,
        location=location,
        tag=category,
        highlights=highlights[:5],
        transport_line=transport_summary,
        strip_labels=[spot_name, location + " food", location + " scenic"],
    )
    return [card]


# ─────────────────────────────────────────────────────────────────────────────
# Caption 模板（附帶按讚 + 追蹤引導）
# ─────────────────────────────────────────────────────────────────────────────

def generate_caption(destination: str, content_type: str, hook: str = "") -> str:
    """生成 IG 貼文 caption"""
    h = hook or f"去過 {destination} 的 你一定懂這種感覺 🧳"
    return f"""{h}

整理了最完整的 {destination} 攻略給你
機票 + 住宿 + 景點 優惠連結都在主頁 🔗

❤️ 按讚讓更多人看到這篇攻略
🔔 追蹤 @taiwan.travel.deals 不錯過最新優惠
💬 留言「{destination}」我幫你整理行程 👇

#{destination}旅遊 #{destination}攻略 #台灣旅遊 #旅遊攻略 #機票優惠"""


# =============================================================================
# 新版 4 卡片架構：地點 / 美食+價格 / 交通+票價 / 注意事項
# =============================================================================

# ── Affiliate 連結模板 ────────────────────────────────────────────────────────
_KLOOK_AID  = "121163"
_KLOOK_ADID = "1276621"
_KKDAY_CID  = "25041"
_AVIASALES_URL = "https://aviasales.tp.st/eQqmPCwf"   # 機票比價
_TRIPCOM_URL   = "https://www.trip.com/t/1vZkBdFMVq3" # 機票+飯店

def klook_link(activity_id: str) -> str:
    return f"https://www.klook.com/zh-TW/activity/{activity_id}/?aid={_KLOOK_AID}&aff_adid={_KLOOK_ADID}"

def klook_search(query: str) -> str:
    return f"https://www.klook.com/zh-TW/search-results/?query={query}&aid={_KLOOK_AID}&aff_adid={_KLOOK_ADID}"

def kkday_link(product_id: str) -> str:
    return f"https://www.kkday.com/zh-tw/product/{product_id}?cid={_KKDAY_CID}"

def kkday_search(query: str) -> str:
    return f"https://www.kkday.com/zh-tw/search?q={query}&cid={_KKDAY_CID}"


# ── 目的地資料庫 ──────────────────────────────────────────────────────────────
DEALS_DB = {
    "東京": {
        "hook": "🇯🇵 去東京不知道這些 等於白去！",
        "intro_items": [
            "淺草寺：東京最古老寺廟 雷門大燈籠必拍",
            "TeamLab Planets：沉浸式數位藝術 超出片",
            "涉谷天空展望台：360度夜景 浪漫約會必去",
            "豐洲市場：海鮮直送 可參觀鮪魚競標",
            "原宿竹下通：日本潮流聖地 限定甜點必買",
        ],
        "food_items": [
            ("玉子燒（築地場外市場）", "¥500起", "現烤限定 台灣沒有"),
            ("海膽丼（豐洲市場）", "¥2,800起", "北海道直送 新鮮度最高"),
            ("近江和牛握壽司", "¥3,500起", "高級和牛 台灣沒進口"),
            ("天婦羅定食（淺草）", "¥1,500起", "江戶傳統炸法 外脆內嫩"),
            ("抹茶霜淇淋（原宿）", "¥500", "日本茶園直送抹茶"),
        ],
        "tickets": [
            {"name": "TeamLab Planets 門票",  "price": "¥3,200", "save": "Klook 享優惠", "platform": "Klook", "url": klook_link("78278")},
            {"name": "涉谷天空展望台",         "price": "¥2,000", "save": "Klook 9折",   "platform": "Klook", "url": klook_link("37843")},
            {"name": "淺草人力車體驗",          "price": "¥3,000", "save": "Klook 優惠",  "platform": "Klook", "url": klook_search("淺草人力車")},
            {"name": "東京迪士尼樂園門票",      "price": "¥10,900","save": "KKday 搶早鳥","platform": "KKday", "url": kkday_search("東京迪士尼")},
        ],
        "transport": [
            "Suica IC卡：充值即用 全東京電車通行",
            "7日地鐵周遊券：¥1,500 無限搭地鐵",
            "成田→市區：N'EX 約60分 ¥3,070",
            "羽田→市區：京急線 約40分 ¥650",
        ],
        "warnings": [
            "現金為主！許多老店不收信用卡",
            "築地場外市場 週三公休 去前要確認",
            "TeamLab 旺季需提前 2 週線上預約",
            "JR Pass 只有行程超過 ¥50,000 才划算",
            "東京迪士尼假日限量票 建議提早 Klook 買",
        ],
    },
    "長灘島": {
        "hook": "🏖️ 長灘島不只有白沙灘！這些必做的你知道嗎？",
        "intro_items": [
            "白沙灘（White Beach）：細白沙配清澈藍海 世界頂級",
            "S1沙灘日落：每天夕陽超美 必拍打卡點",
            "浮潛/潛水：珊瑚礁豐富 海底世界色彩繽紛",
            "帆船出海：傳統螃蟹船出海看日落 超浪漫",
            "D'Mall購物街：伴手禮 珊瑚飾品 台灣平價3倍",
        ],
        "food_items": [
            ("海鮮BBQ（D'Talipapa市場）", "₱300起", "自選海鮮現烤 台灣沒這味"),
            ("椰子蟹（Coconut Crab）", "₱800起", "菲律賓限定 台灣吃不到"),
            ("芒果冰沙（Fresh Mango）", "₱100", "菲律賓芒果甜度爆表"),
            ("烤乳豬（Lechon Kawali）", "₱250起", "酥脆豬皮 在地節慶必吃"),
            ("Halo-Halo刨冰", "₱120起", "菲律賓傳統甜點 消暑必點"),
        ],
        "tickets": [
            {"name": "長灘島帆船日落遊覽", "price": "₱800起", "save": "Klook 優惠", "platform": "Klook", "url": klook_search("長灘島帆船")},
            {"name": "浮潛+珊瑚礁探索", "price": "₱1,200起", "save": "Klook 套票", "platform": "Klook", "url": klook_search("長灘島浮潛")},
            {"name": "ATV越野車體驗", "price": "₱800起", "save": "KKday 優惠", "platform": "KKday", "url": kkday_search("長灘島ATV")},
        ],
        "transport": [
            "台北→馬尼拉→長灘島：轉機約5小時",
            "卡利博機場：落地搭巴士+船 約2小時",
            "長灘島內交通：三輪車 ₱50起 摩托車 ₱300/天",
            "D'Mall到白沙灘：步行5分鐘",
        ],
        "warnings": [
            "白沙灘禁帶玻璃瓶 罰款很重",
            "D'Talipapa市場要先殺價 開價都是台灣客價",
            "防曬乳要帶礁岩友善型 菲律賓有規定",
            "海上活動記得帶防水袋 手機掉海裡沒救",
            "雨季（6-11月）浪大 建議12-5月旺季去",
        ],
    },
    "大阪": {
        "hook": "🏯 大阪吃貨天堂 這幾樣沒吃到等於沒去！",
        "intro_items": [
            "道頓堀：霓虹招牌打卡聖地 美食一條街",
            "黑門市場：大阪廚房 海鮮刺身現場吃",
            "大阪城：日本三大名城 免費公園超大",
            "心齋橋：購物天堂 藥妝伴手禮必掃",
            "通天閣：大阪下町文化 老街超有味道",
        ],
        "food_items": [
            ("章魚燒（會津屋元祖）", "¥600/8顆", "大阪發源地 正宗口感"),
            ("大阪燒（千房）",         "¥1,200起",  "豬肉大葉版 台灣沒有"),
            ("黑門市場海膽",           "¥2,500起",  "現場開殼即食"),
            ("串炸（新世界）",          "¥100/串起",  "不能沾兩次醬汁！"),
            ("自由軒咖哩（難波）",      "¥800起",    "明治36年老店 特製生蛋"),
        ],
        "tickets": [
            {"name": "大阪周遊卡（1日）", "price": "¥2,800", "save": "Klook 優惠",  "platform": "Klook", "url": klook_search("大阪周遊卡")},
            {"name": "USJ 環球影城門票", "price": "¥8,600起","save": "KKday 早鳥",  "platform": "KKday", "url": kkday_search("大阪環球影城")},
            {"name": "大阪城天守閣",      "price": "¥600",    "save": "周遊卡免費", "platform": "Klook", "url": klook_search("大阪城")},
        ],
        "transport": [
            "大阪周遊卡：涵蓋地鐵 + 40個景點免費入場",
            "關西機場→難波：南海電鐵 約45分 ¥920",
            "大阪地鐵一日券：¥800 無限搭",
            "自行車租借：¥1,000/天 市區最方便",
        ],
        "warnings": [
            "串炸醬汁不能沾兩次！觀光客地雷",
            "黑門市場週一多攤位公休",
            "USJ 哈利波特區旺季需搶 Express Pass",
            "心齋橋假日人潮爆多 建議早上9點前去",
            "藥妝店比價要注意 有些含稅反而貴",
        ],
    },
}


# ── 共用 footer + 互動條 ──────────────────────────────────────────────────────
def _footer_bar(img: Image.Image) -> Image.Image:
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


def _panel_items_with_emoji(img: Image.Image, items: list,
                             panel_top: int, panel_bot: int,
                             font_size: int = 34) -> Image.Image:
    """在奶油面板內畫 emoji + 文字條列（pilmoji）"""
    draw = ImageDraw.Draw(img)
    fnt_item = fr(font_size)
    fnt_icon = fe(font_size + 2)
    ICON_W = 52
    item_y = panel_top + 12
    line_h = font_size + 10

    with Pilmoji(img) as pm:
        for item in items:
            if item_y + line_h > panel_bot - 8:
                break
            icon = auto_icon(item)
            pm.text((58, item_y), icon, font=fnt_icon, fill=DARK_TXT)
            lines = wrap_text(item, fnt_item, 930, draw)
            for j, line in enumerate(lines):
                draw.text((58 + ICON_W, item_y + 4 + j * line_h), line,
                          font=fnt_item, fill=DARK_TXT)
            item_y += max(len(lines), 1) * line_h + 10
    return img


def _card_base(destination: str, bg_theme: str,
               tag: str, tag_color,
               title: str, subtitle: str = "") -> Image.Image:
    """卡片基底：背景 + 漸層 + 標籤 + 大標題"""
    bg = get_travel_photo(destination, bg_theme, SIZE)
    bg = ImageEnhance.Brightness(bg).enhance(0.70)
    img = warm_overlay(bg)

    draw = ImageDraw.Draw(img)
    draw.text((52, 38), destination, font=fr(32), fill=(255, 252, 248, 55))

    # 標籤
    fnt_tag = fb(34)
    tag_str = f"  \\ {tag} /  "
    bb = draw.textbbox((0, 0), tag_str, font=fnt_tag)
    tw = bb[2] - bb[0]
    tx = (SIZE[0] - tw) // 2
    tag_y = 168
    img = ov_rounded(img, [tx-16, tag_y, tx+tw+16, tag_y+(bb[3]-bb[1])+14],
                     20, (*tag_color, 220))
    draw = ImageDraw.Draw(img)
    draw.text((tx, tag_y+7), tag_str, font=fnt_tag, fill=WARM_WHITE)

    # 大標題
    fnt_big = fb(108)
    bb2 = draw.textbbox((0, 0), title, font=fnt_big)
    if bb2[2]-bb2[0] > 980:
        fnt_big = fb(80)
        bb2 = draw.textbbox((0, 0), title, font=fnt_big)
    tx2 = (SIZE[0] - (bb2[2]-bb2[0])) // 2
    shadow(draw, (tx2, 228), title, fnt_big, WARM_WHITE)

    if subtitle:
        fnt_sub = fb(46)
        bb3 = draw.textbbox((0, 0), subtitle, font=fnt_sub)
        tx3 = (SIZE[0] - (bb3[2]-bb3[0])) // 2
        shadow(draw, (tx3, 368), subtitle, fnt_sub, (220, 200, 170))

    return img


# ── 卡片1：地點介紹 ───────────────────────────────────────────────────────────
def make_intro_card(destination: str, intro_items: list,
                    subtitle: str = "") -> Image.Image:
    img = _card_base(destination, "landmark scenic", "必去景點",
                     WARM_ORANGE, destination, subtitle)

    panel_top, panel_bot = 440, 960
    img = ov_rounded(img, [38, panel_top, SIZE[0]-38, panel_bot], 16, (*CREAM, 226))
    draw = ImageDraw.Draw(img)
    hdr = "| 去了一定後悔沒去 |"
    bb_h = draw.textbbox((0, 0), hdr, font=fr(28))
    draw.text(((SIZE[0]-(bb_h[2]-bb_h[0]))//2, panel_top+12), hdr, font=fr(28), fill=LIGHT_TXT)
    draw.line([(60, panel_top+50), (SIZE[0]-60, panel_top+50)], fill=(*CREAM_DIM, 255), width=2)

    img = _panel_items_with_emoji(img, intro_items[:5], panel_top+56, panel_bot-10, 34)
    return _footer_bar(img)


# ── 卡片2：美食 + 價格 ────────────────────────────────────────────────────────
def make_food_card(destination: str,
                   food_items: list  # [("店名/品項", "¥XXX起", "說明"), ...]
                   ) -> Image.Image:
    img = _card_base(destination, "food market street", "必吃清單",
                     TEAL_TAG, destination, "在地限定 台灣吃不到")

    panel_top, panel_bot = 440, 980
    img = ov_rounded(img, [38, panel_top, SIZE[0]-38, panel_bot], 16, (*CREAM, 226))
    draw = ImageDraw.Draw(img)
    hdr = "| 台灣沒有的才值得去吃 |"
    bb_h = draw.textbbox((0, 0), hdr, font=fr(28))
    draw.text(((SIZE[0]-(bb_h[2]-bb_h[0]))//2, panel_top+12), hdr, font=fr(28), fill=LIGHT_TXT)
    draw.line([(60, panel_top+50), (SIZE[0]-60, panel_top+50)], fill=(*CREAM_DIM, 255), width=2)

    fnt_name  = fb(34)
    fnt_price = fb(30)
    fnt_note  = fr(26)
    fnt_icon  = fe(34)
    y = panel_top + 60
    ICON_W = 50
    PRICE_BADGE_COLOR = (210, 118, 38)

    draw = ImageDraw.Draw(img)
    with Pilmoji(img) as pm:
        for name, price, note in food_items[:5]:
            if y + 70 > panel_bot - 8:
                break
            icon = auto_icon(name)
            pm.text((58, y + 2), icon, font=fnt_icon, fill=DARK_TXT)

            # 店名
            draw.text((58 + ICON_W, y), name, font=fnt_name, fill=DARK_TXT)

            # 價格 badge（右側）
            bb_p = draw.textbbox((0, 0), price, font=fnt_price)
            pw = bb_p[2] - bb_p[0]
            px = SIZE[0] - pw - 70
            img = ov_rounded(img, [px-10, y+2, px+pw+10, y+38], 12,
                             (*PRICE_BADGE_COLOR, 210))
            draw = ImageDraw.Draw(img)
            draw.text((px, y+5), price, font=fnt_price, fill=WARM_WHITE)

            # 說明小字
            draw.text((58 + ICON_W, y + 40), note, font=fnt_note, fill=MID_TXT)
            y += 84

            # 分隔線
            if y < panel_bot - 70:
                draw.line([(60, y-4), (SIZE[0]-60, y-4)], fill=(*CREAM_DIM, 180), width=1)

    return _footer_bar(img)


# ── 卡片3：交通 + 票價 ────────────────────────────────────────────────────────
def make_transport_card(destination: str,
                        transport_items: list,   # ["說明文字", ...]
                        ticket_items: list        # [{"name","price","save","platform"}, ...]
                        ) -> Image.Image:
    img = _card_base(destination, "train station transport", "交通 + 票券",
                     (62, 100, 172), destination, "省錢攻略一次看")

    # 上半：交通
    t_top, t_bot = 440, 690
    img = ov_rounded(img, [38, t_top, SIZE[0]-38, t_bot], 16, (*CREAM, 224))
    draw = ImageDraw.Draw(img)
    hdr1 = "| 交通方式 |"
    bb1 = draw.textbbox((0, 0), hdr1, font=fr(28))
    draw.text(((SIZE[0]-(bb1[2]-bb1[0]))//2, t_top+10), hdr1, font=fr(28), fill=LIGHT_TXT)
    draw.line([(60, t_top+46), (SIZE[0]-60, t_top+46)], fill=(*CREAM_DIM, 255), width=2)
    img = _panel_items_with_emoji(img, transport_items[:4], t_top+52, t_bot-6, 30)

    # 下半：票券
    k_top, k_bot = 708, 990
    img = ov_rounded(img, [38, k_top, SIZE[0]-38, k_bot], 16, (*CREAM, 224))
    draw = ImageDraw.Draw(img)
    hdr2 = "| 景點票價 + 優惠管道 |"
    bb2 = draw.textbbox((0, 0), hdr2, font=fr(28))
    draw.text(((SIZE[0]-(bb2[2]-bb2[0]))//2, k_top+10), hdr2, font=fr(28), fill=LIGHT_TXT)
    draw.line([(60, k_top+46), (SIZE[0]-60, k_top+46)], fill=(*CREAM_DIM, 255), width=2)

    fnt_name = fb(30)
    fnt_info = fr(26)
    y = k_top + 56
    KLOOK_COLOR = (255, 88, 0)
    KKDAY_COLOR = (0, 120, 210)

    draw = ImageDraw.Draw(img)
    for t in ticket_items[:4]:
        if y + 60 > k_bot - 6:
            break
        draw.text((60, y), t["name"], font=fnt_name, fill=DARK_TXT)

        # 價格
        draw.text((60, y + 34), t["price"], font=fnt_info, fill=MID_TXT)

        # 平台 badge
        plat = t.get("platform", "Klook")
        save = t.get("save", "")
        badge_txt = f"{plat} {save}".strip()
        bc = KLOOK_COLOR if plat == "Klook" else KKDAY_COLOR
        bb_b = draw.textbbox((0, 0), badge_txt, font=fnt_info)
        bw = bb_b[2] - bb_b[0]
        bx = SIZE[0] - bw - 72
        img = ov_rounded(img, [bx-8, y+4, bx+bw+8, y+34], 10, (*bc, 215))
        draw = ImageDraw.Draw(img)
        draw.text((bx, y+7), badge_txt, font=fnt_info, fill=WARM_WHITE)

        y += 66
        if y < k_bot - 50:
            draw.line([(60, y-4), (SIZE[0]-60, y-4)], fill=(*CREAM_DIM, 160), width=1)

    return _footer_bar(img)


# ── 卡片4：注意事項 ───────────────────────────────────────────────────────────
def make_tips_card(destination: str, warnings: list) -> Image.Image:
    img = _card_base(destination, "travel warning tips", "避雷提醒",
                     RED_TAG, "去前必看", f"{destination} 旅遊踩坑警告")

    panel_top, panel_bot = 440, 970
    img = ov_rounded(img, [38, panel_top, SIZE[0]-38, panel_bot], 16, (*CREAM, 226))
    draw = ImageDraw.Draw(img)
    hdr = "| 不知道這些 很容易踩坑 |"
    bb_h = draw.textbbox((0, 0), hdr, font=fr(28))
    draw.text(((SIZE[0]-(bb_h[2]-bb_h[0]))//2, panel_top+12), hdr, font=fr(28), fill=LIGHT_TXT)
    draw.line([(60, panel_top+50), (SIZE[0]-60, panel_top+50)], fill=(*CREAM_DIM, 255), width=2)

    fnt_item = fr(34)
    fnt_icon = fe(34)
    ICON_W = 52
    y = panel_top + 60
    line_h = 44
    WARNING_COLORS = [(195, 72, 58), (210, 118, 38), (138, 100, 178),
                      (62, 148, 142), (88, 140, 80)]

    draw = ImageDraw.Draw(img)
    with Pilmoji(img) as pm:
        for i, w in enumerate(warnings[:5]):
            if y + line_h > panel_bot - 10:
                break
            # 帶警告/提示 icon
            icon = auto_icon(w) if any(kw in w for kw in ["注意", "避雷", "踩坑", "不能", "提前", "確認", "建議"]) else "⚠️"
            pm.text((58, y), icon, font=fnt_icon, fill=WARNING_COLORS[i % len(WARNING_COLORS)])
            lines = wrap_text(w, fnt_item, 930, draw)
            for j, line in enumerate(lines):
                draw.text((58 + ICON_W, y + 4 + j * line_h), line,
                          font=fnt_item, fill=DARK_TXT)
            y += max(len(lines), 1) * line_h + 14

    return _footer_bar(img)


# ── 主介面：generate_destination_carousel ─────────────────────────────────────
def generate_destination_carousel(destination: str) -> tuple:
    """
    生成 4 張輪播圖 + caption（含優惠連結）
    回傳 (cards: list[Image], caption: str)
    """
    data = DEALS_DB.get(destination)
    if not data:
        # 備用：用舊版 power card
        cards = [make_power_card(
            destination=destination, tag="攻略",
            title=destination, subtitle="旅遊必看",
            panel_header="行程一次看懂",
            items=[f"{destination} 精選景點、美食、交通一次整理"],
            strip_labels=[destination] * 3,
        )]
        return cards, generate_caption(destination, "guide")

    cards = [
        make_intro_card(destination, data["intro_items"]),
        make_food_card(destination, data["food_items"]),
        make_transport_card(destination, data["transport"], data["tickets"]),
        make_tips_card(destination, data["warnings"]),
    ]

    # Caption
    hook = data.get("hook", f"🧳 {destination} 旅遊攻略整理好了！")

    deals_lines = []
    for t in data.get("tickets", []):
        deals_lines.append(f"  • {t['name']} {t['price']} → {t['platform']} 有優惠")

    deals_str = "\n".join(deals_lines)
    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"

    caption = f"""{hook}

這篇幫你整理好了：
景點推薦 / 在地限定美食 / 交通省錢 / 避雷提醒

票券優惠：
{deals_str}

🔗 Klook / KKday / 機票比價 優惠連結全在 👇
{linkinbio}

❤️ 按讚讓更多人看到這篇攻略
🔔 追蹤 @taiwan.travel.deals 不錯過最新優惠
💬 留言「{destination}」我幫你整理完整行程 👇

#{destination}旅遊 #{destination}攻略 #{destination}必去 #台灣旅遊 #旅遊省錢 #機票優惠 #Klook優惠"""

    return cards, caption
