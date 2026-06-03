"""
K 線型態輪播（單蠟燭風格）
每張圖一種 K 線型態：左側大圖單蠟燭 + 右側解說文字
仿 @cryptosnakeboss 極簡淡藍灰風格
"""
import os
import random
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
from font_paths import FONT_BOLD, FONT_REG

W, H    = 1080, 1080
BG      = (235, 240, 248)    # 淡藍灰背景
BLACK   = (30,  30,  30)
GREY    = (140, 140, 140)
GREEN   = (22,  163,  74)
RED     = (210,  45,  45)
WHITE   = (255, 255, 255)

def fb(s): return ImageFont.truetype(FONT_BOLD, s)
def fr(s): return ImageFont.truetype(FONT_REG,  s)


# ── 單蠟燭資料庫 ──────────────────────────────────────────────────────────────

SINGLE_CANDLES = {
    "big_bullish": {
        "title":   "大陽線",
        "signal":  "強勢信號",
        "color":   GREEN,
        "bullish": True,
        "body_ratio":        0.85,
        "upper_wick_ratio":  0.075,
        "lower_wick_ratio":  0.075,
        "desc": ["多頭氣勢極強", "價格一路走高，強勢看多"],
    },
    "big_bearish": {
        "title":   "大陰線",
        "signal":  "強勢信號",
        "color":   RED,
        "bullish": False,
        "body_ratio":        0.85,
        "upper_wick_ratio":  0.075,
        "lower_wick_ratio":  0.075,
        "desc": ["空頭全面佔優", "價格一路重挫，強勢看空"],
    },
    "hammer": {
        "title":   "錘子線",
        "signal":  "看漲信號",
        "color":   GREEN,
        "bullish": True,
        "body_ratio":        0.22,
        "upper_wick_ratio":  0.06,
        "lower_wick_ratio":  0.72,
        "desc": ["下影線長，下方支撐強勁", "止跌回升"],
    },
    "inverted_hammer": {
        "title":   "倒錘子線",
        "signal":  "看空信號",
        "color":   RED,
        "bullish": False,
        "body_ratio":        0.22,
        "upper_wick_ratio":  0.72,
        "lower_wick_ratio":  0.06,
        "desc": ["上影線長", "上方壓力沉重，反彈無力"],
    },
    "shooting_star": {
        "title":   "流星線",
        "signal":  "看空信號",
        "color":   RED,
        "bullish": False,
        "body_ratio":        0.18,
        "upper_wick_ratio":  0.76,
        "lower_wick_ratio":  0.06,
        "desc": ["上影線極長，高點賣壓巨大", "高位反轉信號"],
    },
    "small_bullish": {
        "title":   "小陽線",
        "signal":  "觀望信號",
        "color":   GREEN,
        "bullish": True,
        "body_ratio":        0.28,
        "upper_wick_ratio":  0.36,
        "lower_wick_ratio":  0.36,
        "desc": ["漲勢溫和，處於窄幅震盪", "建議先觀望"],
    },
    "small_bearish": {
        "title":   "小陰線",
        "signal":  "觀望信號",
        "color":   RED,
        "bullish": False,
        "body_ratio":        0.28,
        "upper_wick_ratio":  0.36,
        "lower_wick_ratio":  0.36,
        "desc": ["跌勢溫和", "市場波動縮小，暫時觀望"],
    },
    "doji_bullish": {
        "title":   "十字星",
        "signal":  "反轉信號",
        "color":   GREEN,
        "bullish": True,
        "body_ratio":        0.0,
        "upper_wick_ratio":  0.50,
        "lower_wick_ratio":  0.50,
        "desc": ["多空力道僵持不下", "是趨勢反轉信號"],
    },
    "doji_bearish": {
        "title":   "十字星",
        "signal":  "反轉信號",
        "color":   RED,
        "bullish": False,
        "body_ratio":        0.0,
        "upper_wick_ratio":  0.50,
        "lower_wick_ratio":  0.50,
        "desc": ["多空力道僵持不下", "是趨勢反轉信號"],
    },
    "marubozu_bull": {
        "title":   "光頭光腳陽線",
        "signal":  "極強多頭",
        "color":   GREEN,
        "bullish": True,
        "body_ratio":        1.0,
        "upper_wick_ratio":  0.0,
        "lower_wick_ratio":  0.0,
        "desc": ["開盤即最低，收盤即最高", "多頭完全主導市場"],
    },
    "marubozu_bear": {
        "title":   "光頭光腳陰線",
        "signal":  "極強空頭",
        "color":   RED,
        "bullish": False,
        "body_ratio":        1.0,
        "upper_wick_ratio":  0.0,
        "lower_wick_ratio":  0.0,
        "desc": ["開盤即最高，收盤即最低", "空頭完全主導市場"],
    },
    "spinning_top_bull": {
        "title":   "紡錘線（多）",
        "signal":  "猶豫信號",
        "color":   GREEN,
        "bullish": True,
        "body_ratio":        0.20,
        "upper_wick_ratio":  0.40,
        "lower_wick_ratio":  0.40,
        "desc": ["多空勢均力敵", "方向未定，等待突破確認"],
    },
}

# 標準 8 種（每次發文用這組保持一致性）
DEFAULT_KEYS = [
    "big_bullish", "hammer", "small_bullish", "doji_bullish",
    "big_bearish", "inverted_hammer", "small_bearish", "doji_bearish",
]


# ── 繪製工具 ────────────────────────────────────────────────────────────────

def _canvas():
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    return img, draw


def _brand(draw):
    """底部浮水印：IG 相機圖示 + WYCBOTAI2026"""
    color  = GREY
    handle = "WYCBOTAI2026"
    font   = fr(28)
    bb     = draw.textbbox((0, 0), handle, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    icon_sz = 34
    gap     = 10
    total_w = icon_sz + gap + tw
    sx = (W - total_w) // 2
    cy = H - 52

    # 相機外框
    draw.rounded_rectangle(
        [sx, cy - icon_sz // 2, sx + icon_sz, cy + icon_sz // 2],
        radius=8, outline=color, width=2
    )
    # 鏡頭圓
    cr = icon_sz // 4 - 1
    draw.ellipse(
        [sx + icon_sz // 2 - cr, cy - cr, sx + icon_sz // 2 + cr, cy + cr],
        outline=color, width=2
    )
    # 閃光燈小點
    dot = 4
    draw.ellipse(
        [sx + icon_sz - dot * 2 - 2, cy - icon_sz // 2 + 4,
         sx + icon_sz - dot - 2,     cy - icon_sz // 2 + 4 + dot],
        fill=color
    )
    # 文字
    draw.text((sx + icon_sz + gap, cy - th // 2 - 1), handle, font=font, fill=color)


def _draw_single_candle(draw, cx, cy, total_h, cdata, body_w=140):
    """在 (cx, cy) 中心繪製單根蠟燭，total_h 為總高度"""
    color   = cdata["color"]
    top_y   = cy - total_h // 2
    bot_y   = cy + total_h // 2

    upper_h = int(total_h * cdata["upper_wick_ratio"])
    lower_h = int(total_h * cdata["lower_wick_ratio"])
    body_h  = int(total_h * cdata["body_ratio"])

    high_y    = top_y
    body_top  = top_y + upper_h
    body_bot  = body_top + body_h
    low_y     = bot_y

    # 上影線
    if upper_h > 4:
        draw.line([(cx, high_y), (cx, body_top)], fill=color, width=8)
    # 下影線
    if lower_h > 4:
        draw.line([(cx, body_bot), (cx, low_y)], fill=color, width=8)
    # 實體
    if body_h > 6:
        draw.rectangle([cx - body_w // 2, body_top, cx + body_w // 2, body_bot], fill=color)
    else:
        # 十字星：畫橫線
        draw.line([(cx - body_w // 2, body_top), (cx + body_w // 2, body_top)], fill=color, width=8)


# ── 幻燈片 ──────────────────────────────────────────────────────────────────

def _slide_cover(candle_keys: list) -> Image.Image:
    img, draw = _canvas()

    # 標題
    title = "看懂這些 K 線型態"
    t_font = fb(72)
    bb = draw.textbbox((0, 0), title, font=t_font)
    draw.text(((W - (bb[2] - bb[0])) // 2, 120), title, font=t_font, fill=BLACK)

    # 小蠟燭示意列（左→右顯示幾根）
    preview = [
        {"color": RED,   "bullish": False, "body_ratio": 0.55, "upper_wick_ratio": 0.20, "lower_wick_ratio": 0.25},
        {"color": RED,   "bullish": False, "body_ratio": 0.60, "upper_wick_ratio": 0.18, "lower_wick_ratio": 0.22},
        {"color": GREEN, "bullish": True,  "body_ratio": 0.22, "upper_wick_ratio": 0.06, "lower_wick_ratio": 0.72},
        {"color": GREEN, "bullish": True,  "body_ratio": 0.70, "upper_wick_ratio": 0.15, "lower_wick_ratio": 0.15},
        {"color": GREEN, "bullish": True,  "body_ratio": 0.75, "upper_wick_ratio": 0.12, "lower_wick_ratio": 0.13},
    ]
    cx_start = 230
    cx_step  = 130
    cy_candle = 520
    total_h   = 300
    body_w    = 70
    for i, p in enumerate(preview):
        _draw_single_candle(draw, cx_start + i * cx_step, cy_candle, total_h, p, body_w=body_w)

    # 右上紅色上漲箭頭
    arrow_pts = [(820, 620), (900, 420)]
    draw.line(arrow_pts, fill=RED, width=6)
    # 箭頭尖
    draw.polygon([(900, 420), (880, 450), (920, 450)], fill=RED)

    # 副標題 hook
    sub = "今年多賺 100 萬"
    s_font = fb(68)
    bb2 = draw.textbbox((0, 0), sub, font=s_font)
    draw.text(((W - (bb2[2] - bb2[0])) // 2, 700), sub, font=s_font, fill=RED)

    _brand(draw)
    return img


def _slide_content(cdata: dict) -> Image.Image:
    img, draw = _canvas()

    # 左側大蠟燭
    candle_cx = 270
    candle_cy = 490
    candle_h  = 500
    body_w    = 150
    _draw_single_candle(draw, candle_cx, candle_cy, candle_h, cdata, body_w=body_w)

    # 右側文字區
    tx = 480
    ty = 330

    # 信號標籤（彩色圓點 + 信號文字）
    dot_r = 14
    draw.ellipse([tx, ty + 4, tx + dot_r * 2, ty + 4 + dot_r * 2], fill=cdata["color"])
    sig_font = fr(44)
    draw.text((tx + dot_r * 2 + 12, ty), cdata["signal"], font=sig_font, fill=cdata["color"])

    # 蠟燭名稱（粗體大字）
    name_font = fb(72)
    ty += 64
    draw.text((tx, ty), cdata["title"], font=name_font, fill=BLACK)

    # 描述行
    ty += 90
    for line in cdata["desc"]:
        draw.text((tx, ty), line, font=fr(44), fill=BLACK)
        ty += 58

    _brand(draw)
    return img


def _slide_last() -> Image.Image:
    img, draw = _canvas()

    lines = [
        ("看懂 K 線型態", fb(62), BLACK,  0),
        ("就像看懂地圖一樣", fb(52), BLACK, 76),
        ("找對方向才不會迷路", fr(44), GREY, 148),
    ]
    base_y = 240
    for text, font, color, dy in lines:
        bb = draw.textbbox((0, 0), text, font=font)
        draw.text(((W - (bb[2] - bb[0])) // 2, base_y + dy), text, font=font, fill=color)

    # 分隔線
    draw.line([(200, 430), (880, 430)], fill=(210, 215, 225), width=2)

    # CTA
    cta_lines = [
        ("留言「K線」", fb(74), RED,   0),
        ("我傳每日信號給你", fb(58), BLACK, 92),
    ]
    cta_y = 500
    for text, font, color, dy in cta_lines:
        bb = draw.textbbox((0, 0), text, font=font)
        draw.text(((W - (bb[2] - bb[0])) // 2, cta_y + dy), text, font=font, fill=color)

    # 追蹤提示
    follow_text = "追蹤 @wycbotai2026 每日學技術分析"
    ft_font = fr(38)
    bb = draw.textbbox((0, 0), follow_text, font=ft_font)
    draw.text(((W - (bb[2] - bb[0])) // 2, 730), follow_text, font=ft_font, fill=GREY)

    _brand(draw)
    return img


# ── 主入口 ────────────────────────────────────────────────────────────────────

def generate_kline_single_post(candle_keys: list = None) -> tuple:
    """
    生成單蠟燭風格 K 線輪播。
    candle_keys: 指定蠟燭類型清單，預設用 DEFAULT_KEYS
    回傳 (slides: list[PIL.Image], caption: str)
    """
    if candle_keys is None:
        candle_keys = DEFAULT_KEYS

    slides = []

    # 封面
    slides.append(_slide_cover(candle_keys))

    # 每種蠟燭一張
    for key in candle_keys:
        if key in SINGLE_CANDLES:
            slides.append(_slide_content(SINGLE_CANDLES[key]))

    # CTA 最後一張
    slides.append(_slide_last())

    # 文案
    names = "、".join(
        SINGLE_CANDLES[k]["title"] for k in candle_keys if k in SINGLE_CANDLES
    )
    caption = (
        f"K 線型態看懂了嗎？\n\n"
        f"本篇教學涵蓋：{names}\n\n"
        f"這幾種 K 線是市場最常出現的信號，\n"
        f"看懂它們才能找對進場時機！\n\n"
        f"WycBotAI AI 每日自動掃描 K 線信號，\n"
        f"讓你不再靠感覺，用邏輯交易。\n\n"
        f"💬 留言「K線」取得每日 K 線信號\n\n"
        f"#K線形態 #技術分析 #加密貨幣 #蠟燭圖 #WycBotAI #聰明錢"
    )
    return slides, caption


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    slides, caption = generate_kline_single_post()
    out = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out, exist_ok=True)
    for i, s in enumerate(slides):
        path = os.path.join(out, f"kline_single_{i+1}.jpg")
        s.save(path, quality=95)
        print(f"  saved: {path}")
    print(f"\nCaption:\n{caption}")
