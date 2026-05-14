"""
旅遊優惠圖片自動生成模組
生成 3 張輪播圖：特價主圖、亮點介紹、CTA
使用 Pillow 合成文字、背景、漸層
"""
import os
import io
import zipfile
import random
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

FONT_PATH = os.path.join(os.path.dirname(__file__), "NotoSansTC-Bold.ttf")
SIZE = (1080, 1080)

# 品牌配色
PURPLE = (102, 50, 150)
DARK_PURPLE = (40, 15, 70)
YELLOW = (255, 200, 0)
WHITE = (255, 255, 255)
LIGHT_BLUE = (200, 220, 255)
GRAY = (180, 180, 180)


# ──────────────────────────────────────────
# 字型
# ──────────────────────────────────────────

_font_cache: dict = {}
_download_attempted = False


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """取得字型（有快取，避免重複下載）"""
    global _download_attempted

    if size in _font_cache:
        return _font_cache[size]

    # 系統字型（優先，最快）
    system_fonts = [
        "C:/Windows/Fonts/msjhbd.ttc",   # Microsoft JhengHei Bold（Windows）
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/mingliu.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Bold.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in system_fonts:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                _font_cache[size] = font
                return font
            except Exception:
                continue

    # 本地快取（已下載過）
    if os.path.exists(FONT_PATH):
        try:
            font = ImageFont.truetype(FONT_PATH, size)
            _font_cache[size] = font
            return font
        except Exception:
            pass

    # 嘗試下載（只試一次）
    if not _download_attempted:
        _download_attempted = True
        _download_font()
        if os.path.exists(FONT_PATH):
            try:
                font = ImageFont.truetype(FONT_PATH, size)
                _font_cache[size] = font
                return font
            except Exception:
                pass

    font = ImageFont.load_default()
    _font_cache[size] = font
    return font


def _download_font():
    """下載 Noto Sans TC Bold 字型（備用方案，Railway Linux 使用）"""
    # 嘗試多個來源
    sources = [
        # GitHub releases - Noto CJK
        "https://github.com/googlefonts/noto-cjk/raw/main/Sans/Variable/TTF/Subset/NotoSansCJKtc-VF.ttf",
        # 備用：WQY Microhei（開源中文字型）
        "https://github.com/anthonyfok/fonts-wqy-microhei/raw/master/wqy-microhei.ttc",
    ]
    for url in sources:
        try:
            print(f"[圖片] 下載字型: {url.split('/')[-1]}")
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(FONT_PATH, "wb") as f:
                    f.write(resp.content)
                print("[圖片] 字型下載完成")
                return
        except Exception as e:
            print(f"[圖片] 字型來源失敗: {e}")
    print("[圖片] 字型下載失敗，使用系統字型")


# ──────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────

def _load_bg(image_url: str) -> Image.Image:
    """下載並裁切背景圖為 1080x1080"""
    try:
        resp = requests.get(image_url, timeout=20)
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        # Crop to square
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        return img.resize(SIZE, Image.LANCZOS)
    except Exception as e:
        print(f"[圖片] 背景下載失敗: {e}")
        # 備用：純色漸層
        fallback = Image.new("RGB", SIZE, DARK_PURPLE)
        return fallback


def _gradient_overlay(img: Image.Image, top_alpha=0, bottom_alpha=210) -> Image.Image:
    """下半漸層黑色疊加"""
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    h = SIZE[1]
    for y in range(h):
        t = (y / h) ** 1.8
        a = int(top_alpha + (bottom_alpha - top_alpha) * t)
        draw.line([(0, y), (SIZE[0], y)], fill=(0, 0, 0, a))
    result = img.convert("RGBA")
    result = Image.alpha_composite(result, overlay)
    return result.convert("RGB")


def _full_overlay(img: Image.Image, alpha=140) -> Image.Image:
    """全面半透明黑色疊加"""
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, alpha))
    result = img.convert("RGBA")
    result = Image.alpha_composite(result, overlay)
    return result.convert("RGB")


def _shadow_text(draw, xy, text, font, color=WHITE):
    """帶陰影的文字"""
    x, y = xy
    for dx, dy in [(3, 3), (-2, 2), (2, -2), (0, 4)]:
        draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 180))
    draw.text(xy, text, font=font, fill=color)


def _center_text(draw, y, text, font, color=WHITE, width=1080):
    """水平置中文字"""
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (width - (bbox[2] - bbox[0])) // 2
    _shadow_text(draw, (x, y), text, font, color)
    return bbox[3] - bbox[1]  # 回傳文字高度


def _parse_deal(deal_info: str):
    """解析優惠資訊字串"""
    route, price, airline = "", "", ""
    parts = deal_info.replace("（", " ").replace("）", " ").split()
    for p in parts:
        if "→" in p:
            route = p
        elif "NT$" in p or "TWD" in p:
            price = p
        elif any(c in p for c in ["航", "桃", "捷", "泰", "新", "越", "港", "國", "長", "華", "韓", "亞"]):
            airline = p
    return route, price, airline


# ──────────────────────────────────────────
# 三張卡片
# ──────────────────────────────────────────

def make_card1_deal(bg_url: str, destination: str, emoji: str, deal_info: str) -> Image.Image:
    """
    第 1 張：主打特價卡
    大圖背景 + 目的地 + 高亮價格
    """
    img = _load_bg(bg_url)
    img = ImageEnhance.Brightness(img).enhance(0.75)
    img = _gradient_overlay(img, top_alpha=0, bottom_alpha=220)
    draw = ImageDraw.Draw(img)

    route, price, airline = _parse_deal(deal_info)

    # 小標：帳號名
    draw.text((55, 50), "@taiwan.travel.deals", font=_get_font(30), fill=(200, 200, 200))

    # 目的地（大字）
    dest_text = f"{emoji}  {destination}"
    _shadow_text(draw, (55, 680), dest_text, _get_font(78))

    # 航線
    if route:
        _shadow_text(draw, (55, 790), f"✈  {route}", _get_font(46), LIGHT_BLUE)

    # 價格（黃底黑字高亮）
    if price:
        price_text = f" 來回 {price} "
        font_p = _get_font(76)
        bbox = draw.textbbox((55, 875), price_text, font=font_p)
        draw.rounded_rectangle(
            [bbox[0] - 6, bbox[1] - 6, bbox[2] + 6, bbox[3] + 6],
            radius=12, fill=YELLOW
        )
        draw.text((55, 875), price_text, font=font_p, fill=(30, 15, 60))

    # 航空公司
    if airline:
        _shadow_text(draw, (55, 980), f"航空：{airline}　　點 bio 連結搶訂 ⬆", _get_font(34), GRAY)

    return img


def make_card2_highlights(bg_url: str, destination: str, emoji: str, highlights: list) -> Image.Image:
    """
    第 2 張：旅遊亮點卡
    背景圖 + 5 個重點條列
    """
    img = _load_bg(bg_url)
    img = ImageEnhance.Brightness(img).enhance(0.45)
    img = _full_overlay(img, alpha=150)
    draw = ImageDraw.Draw(img)

    # 標題
    title = f"{emoji}  {destination} 旅遊亮點"
    _shadow_text(draw, (55, 65), title, _get_font(62))

    # 分隔線
    draw.line([(55, 162), (1025, 162)], fill=(255, 255, 255, 100), width=2)

    # 亮點清單
    y = 195
    for item in highlights[:5]:
        _shadow_text(draw, (70, y), item, _get_font(44))
        y += 145

    # 底部 CTA
    _shadow_text(draw, (55, 980), "更多優惠 → 連結在 bio ⬆", _get_font(36), YELLOW)

    return img


def make_card3_cta(destination: str, emoji: str) -> Image.Image:
    """
    第 3 張：CTA 品牌卡
    漸層背景 + 大箭頭 CTA
    """
    img = Image.new("RGB", SIZE)
    draw = ImageDraw.Draw(img)

    # 漸層背景（紫→粉）
    for y in range(SIZE[1]):
        t = y / SIZE[1]
        r = int(102 + (240 - 102) * t)
        g = int(50 + (90 - 50) * t)
        b = int(150 + (200 - 150) * t)
        draw.line([(0, y), (SIZE[0], y)], fill=(r, g, b))

    # 裝飾圓圈
    for i, (cx, cy, cr) in enumerate([(150, 150, 120), (950, 200, 90), (100, 900, 100), (980, 880, 130)]):
        circle_img = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(circle_img)
        c_draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(255, 255, 255, 20))
        img = Image.alpha_composite(img.convert("RGBA"), circle_img).convert("RGB")

    draw = ImageDraw.Draw(img)

    # 大 emoji
    _center_text(draw, 170, emoji, _get_font(130))

    # 目的地名
    _center_text(draw, 350, destination, _get_font(70))

    # 主標語
    _center_text(draw, 490, "更多旅遊優惠特價", _get_font(60), YELLOW)

    # 大箭頭 CTA
    _center_text(draw, 620, "⬆  連結在 bio", _get_font(82))

    # 帳號名
    _center_text(draw, 830, "@taiwan.travel.deals", _get_font(42), LIGHT_BLUE)

    # 底線 + 品牌名
    draw.line([(200, 915), (880, 915)], fill=(255, 255, 255, 80), width=1)
    _center_text(draw, 935, "Yu 出國旅遊大全", _get_font(40), GRAY)

    return img


# ──────────────────────────────────────────
# 對外介面
# ──────────────────────────────────────────

def generate_deal_carousel(
    destination: str,
    emoji: str,
    deal_info: str,
    image_url: str,
    highlights: list,
) -> list:
    """
    生成特價貼文 3 張輪播圖
    回傳 [PIL Image, PIL Image, PIL Image]
    """
    from travel_data import get_image_url
    lock2 = random.randint(50, 200)
    bg2 = get_image_url(destination, lock=lock2)

    return [
        make_card1_deal(image_url, destination, emoji, deal_info),
        make_card2_highlights(bg2, destination, emoji, highlights),
        make_card3_cta(destination, emoji),
    ]


def generate_tip_carousel(
    topic: str,
    image_url: str,
    highlights: list,
) -> list:
    """
    生成攻略貼文 3 張輪播圖
    """
    from travel_data import get_image_url
    lock2 = random.randint(50, 200)
    bg2 = get_image_url("旅遊", lock=lock2)

    # Card 1：攻略主題封面
    img = _load_bg(image_url)
    img = ImageEnhance.Brightness(img).enhance(0.55)
    img = _gradient_overlay(img, 0, 210)
    draw = ImageDraw.Draw(img)
    _shadow_text(draw, (55, 700), "📖  旅遊攻略", _get_font(52), YELLOW)
    _shadow_text(draw, (55, 790), topic, _get_font(68))
    _shadow_text(draw, (55, 960), "往右滑看重點  →", _get_font(40), GRAY)

    return [
        img,
        make_card2_highlights(bg2, topic, "📌", highlights),
        make_card3_cta(topic, "✈️"),
    ]
