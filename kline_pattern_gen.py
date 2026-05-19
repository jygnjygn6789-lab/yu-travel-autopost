"""
K 線形態教學輪播生成器
PIL 手繪示意圖 + 文字解說，仿 @1336cryptoclub 米白風格
"""
import os, re, json
import anthropic
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from font_paths import FONT_BOLD, FONT_REG

W, H    = 1080, 1080
BG      = (245, 241, 232)
CHART_BG = (235, 230, 218)
BLACK   = (18,  18,  18)
GREY    = (110, 110, 110)
GREEN   = (0,   180, 100)
RED     = (210,  45,  45)
DARK    = (28,  28,  28)
CREAM2  = (225, 219, 205)
WHITE   = (255, 255, 255)

BINGX_URL = os.getenv("BINGX_REFERRAL_URL", "https://bingxdao.com/invite/LKUUM8/")

def fb(s): return ImageFont.truetype(FONT_BOLD, s)
def fr(s): return ImageFont.truetype(FONT_REG,  s)


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        test = cur + ch
        if draw.textbbox((0,0), test, font=font)[2] > max_w and cur:
            lines.append(cur); cur = ch
        else:
            cur = test
    if cur: lines.append(cur)
    return lines


def _canvas():
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    return img, draw


def _brand(draw, dark_mode=False):
    color = (200, 200, 200) if dark_mode else GREY
    draw.text((54, H - 60), "@wycbotai", font=fr(32), fill=color)
    draw.text((W - 260, H - 60), "wycbotai.com", font=fr(32), fill=GREEN)


# ── 蠟燭繪製 ────────────────────────────────────────────────────────────────────

def _draw_candle(draw, cx, open_y, close_y, high_y, low_y,
                 bullish, body_w=52, highlight=False):
    color = GREEN if bullish else RED
    body_top = min(open_y, close_y)
    body_bot = max(open_y, close_y)

    # 高亮外框
    if highlight:
        glow = (0, 230, 130) if bullish else (255, 90, 90)
        draw.rectangle([cx - body_w//2 - 5, body_top - 5,
                        cx + body_w//2 + 5, body_bot + 5], fill=glow)

    # 上影線
    draw.line([(cx, high_y), (cx, body_top)], fill=color, width=4)
    # 下影線
    draw.line([(cx, body_bot), (cx, low_y)], fill=color, width=4)

    # 實體
    if body_bot - body_top < 5:          # 十字星
        draw.line([(cx - body_w//2, body_top),
                   (cx + body_w//2, body_top)], fill=color, width=5)
    else:
        draw.rectangle([cx - body_w//2, body_top,
                        cx + body_w//2, body_bot], fill=color)


def _draw_arrow(draw, x1, y1, x2, y2, color=BLACK, width=2):
    """畫箭頭線段"""
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    # 箭頭頭
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 10
    for da in (0.4, -0.4):
        ax = x2 - size * math.cos(angle - da)
        ay = y2 - size * math.sin(angle - da)
        draw.line([(int(ax), int(ay)), (x2, y2)], fill=color, width=width)


def _draw_pattern_area(img, draw, candles_data: list,
                       ax: int, ay: int, aw: int, ah: int,
                       support_level: float = None,
                       zone: tuple = None,
                       annotations: list = None):
    """
    繪製蠟燭示意圖區域。
    support_level: 畫一條水平支撐線（0~1）
    zone: (low, high) 畫一個半透明進場區域（0~1）
    annotations: list of {"candle_idx", "side": "left/right", "text", "point": "high/low/body"}
    """
    # 背景框
    draw.rounded_rectangle([ax, ay, ax + aw, ay + ah], radius=16, fill=CHART_BG)

    n = len(candles_data)

    # 精確計算價格範圍（自動撐到四周有 8% 留白）
    all_h = [c["h"] for c in candles_data]
    all_l = [c["l"] for c in candles_data]
    pad = (max(all_h) - min(all_l)) * 0.15
    price_max = max(all_h) + pad
    price_min = min(all_l) - pad
    price_range = price_max - price_min

    margin_x = int(aw * 0.06)
    margin_top = int(ah * 0.07)
    margin_bot = int(ah * 0.10)
    draw_w = aw - 2 * margin_x
    draw_h = ah - margin_top - margin_bot

    def to_y(v):
        return int(ay + margin_top + draw_h * (1 - (v - price_min) / price_range))

    # 網格線（4 條水平淡線）
    for gi in range(1, 5):
        gy = ay + margin_top + int(draw_h * gi / 5)
        draw.line([(ax + margin_x, gy), (ax + aw - margin_x, gy)],
                  fill=(210, 204, 192), width=1)

    # 進場區域陰影
    if zone:
        zl, zh = zone
        zy1 = to_y(zh)
        zy2 = to_y(zl)
        overlay = Image.new("RGB", img.size, (0, 200, 120))
        mask = Image.new("L", img.size, 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.rectangle([ax + margin_x, zy1, ax + aw - margin_x, zy2], fill=40)
        img.paste(overlay, mask=mask)
        draw = ImageDraw.Draw(img)   # refresh draw after paste

    # 支撐線
    if support_level is not None:
        sy = to_y(support_level)
        # dashed line
        for sx in range(ax + margin_x, ax + aw - margin_x, 16):
            draw.line([(sx, sy), (min(sx + 10, ax + aw - margin_x), sy)],
                      fill=(0, 180, 100), width=2)
        draw.text((ax + aw - margin_x + 4, sy - 16), "支撐", font=fr(24), fill=GREEN)

    # 蠟燭
    slot_w = draw_w / n
    body_w = max(28, min(56, int(slot_w * 0.62)))

    cx_list = []
    for i, c in enumerate(candles_data):
        cx = int(ax + margin_x + slot_w * i + slot_w / 2)
        cx_list.append(cx)
        oy = to_y(c["o"])
        cy2 = to_y(c["c"])
        hy = to_y(c["h"])
        ly = to_y(c["l"])
        _draw_candle(draw, cx, oy, cy2, hy, ly,
                     c["bullish"], body_w, c.get("highlight", False))

    # 箭頭標籤
    for ann in (annotations or []):
        idx = ann.get("candle_idx", 0)
        if idx >= len(candles_data):
            continue
        c   = candles_data[idx]
        cx  = cx_list[idx]
        pt  = ann.get("point", "low")
        if pt == "high":
            py = to_y(c["h"])
        elif pt == "low":
            py = to_y(c["l"])
        elif pt == "body_mid":
            py = to_y((c["o"] + c["c"]) / 2)
        else:
            py = to_y(c["h"])

        side  = ann.get("side", "right")
        text  = ann.get("text", "")
        color = ann.get("color", BLACK)

        if side == "right":
            lx1 = cx + body_w // 2 + 6
            lx2 = lx1 + 40
            draw.line([(cx, py), (lx2, py)], fill=color, width=2)
            draw.text((lx2 + 6, py - 20), text, font=fb(28), fill=color)
        else:
            lx1 = cx - body_w // 2 - 6
            lx2 = lx1 - 40
            bb  = draw.textbbox((0,0), text, font=fb(28))
            tw  = bb[2] - bb[0]
            draw.line([(cx, py), (lx2, py)], fill=color, width=2)
            draw.text((lx2 - tw - 6, py - 20), text, font=fb(28), fill=color)

    # 底部基線
    base_y = ay + ah - margin_bot // 2
    draw.line([(ax + margin_x, base_y), (ax + aw - margin_x, base_y)],
              fill=(180, 170, 155), width=1)

    return draw


# ── K 線形態資料庫 ─────────────────────────────────────────────────────────────

KLINE_PATTERNS = {
    "hammer": {
        "title":        "錘子線（Hammer）",
        "signal":       "看多反轉信號",
        "signal_color": "green",
        "candles": [
            {"o":0.88,"h":0.90,"l":0.80,"c":0.81,"bullish":False},
            {"o":0.81,"h":0.83,"l":0.74,"c":0.75,"bullish":False},
            {"o":0.75,"h":0.77,"l":0.68,"c":0.69,"bullish":False},
            {"o":0.69,"h":0.71,"l":0.62,"c":0.63,"bullish":False},
            {"o":0.63,"h":0.65,"l":0.56,"c":0.57,"bullish":False},
            {"o":0.57,"h":0.60,"l":0.30,"c":0.59,"bullish":True,"highlight":True},
        ],
        "support_level": 0.35,
        "zone": (0.56, 0.62),
        "annotations": [
            {"candle_idx":5,"point":"low",     "side":"right","text":"長下影線","color":GREEN},
            {"candle_idx":5,"point":"body_mid","side":"left", "text":"小實體",  "color":BLACK},
        ],
        "points": [
            "下影線長度 ≥ 實體的 2 倍",
            "出現在下跌末端 + 支撐位效果最強",
            "ICT：常配合 Order Block 使用",
            "次根確認收高再進場，避免假信號",
        ],
    },
    "shooting_star": {
        "title":        "流星線（Shooting Star）",
        "signal":       "看空反轉信號",
        "signal_color": "red",
        "candles": [
            {"o":0.42,"h":0.44,"l":0.38,"c":0.43,"bullish":True},
            {"o":0.43,"h":0.52,"l":0.42,"c":0.51,"bullish":True},
            {"o":0.51,"h":0.60,"l":0.50,"c":0.59,"bullish":True},
            {"o":0.59,"h":0.68,"l":0.58,"c":0.67,"bullish":True},
            {"o":0.67,"h":0.76,"l":0.66,"c":0.75,"bullish":True},
            {"o":0.75,"h":0.96,"l":0.73,"c":0.76,"bullish":False,"highlight":True},
        ],
        "support_level": None,
        "zone": (0.72, 0.77),
        "annotations": [
            {"candle_idx":5,"point":"high",    "side":"right","text":"長上影線","color":RED},
            {"candle_idx":5,"point":"body_mid","side":"left", "text":"小實體",  "color":BLACK},
        ],
        "points": [
            "上影線長度 ≥ 實體的 2 倍",
            "出現在上漲末端 + 壓力位效果最強",
            "代表機構在高點大量出貨",
            "次根確認收低再做空",
        ],
    },
    "bullish_engulfing": {
        "title":        "看多吞噬（Bullish Engulfing）",
        "signal":       "強烈看多反轉",
        "signal_color": "green",
        "candles": [
            {"o":0.82,"h":0.84,"l":0.74,"c":0.75,"bullish":False},
            {"o":0.75,"h":0.77,"l":0.67,"c":0.68,"bullish":False},
            {"o":0.68,"h":0.70,"l":0.60,"c":0.61,"bullish":False},
            {"o":0.61,"h":0.63,"l":0.53,"c":0.54,"bullish":False},
            {"o":0.54,"h":0.56,"l":0.46,"c":0.47,"bullish":False},
            {"o":0.45,"h":0.68,"l":0.44,"c":0.67,"bullish":True,"highlight":True},
        ],
        "support_level": 0.50,
        "zone": (0.44, 0.50),
        "annotations": [
            {"candle_idx":4,"point":"body_mid","side":"left","text":"被吞噬","color":RED},
            {"candle_idx":5,"point":"high",    "side":"right","text":"完全吞噬","color":GREEN},
        ],
        "points": [
            "綠色實體完全包住前一根紅色實體",
            "成交量放大確認效果更強",
            "ICT：常出現在 Order Block 下緣",
            "代表機構大資金強力吸籌",
        ],
    },
    "bearish_engulfing": {
        "title":        "看空吞噬（Bearish Engulfing）",
        "signal":       "強烈看空反轉",
        "signal_color": "red",
        "candles": [
            {"o":0.38,"h":0.46,"l":0.37,"c":0.45,"bullish":True},
            {"o":0.45,"h":0.54,"l":0.44,"c":0.53,"bullish":True},
            {"o":0.53,"h":0.62,"l":0.52,"c":0.61,"bullish":True},
            {"o":0.61,"h":0.70,"l":0.60,"c":0.69,"bullish":True},
            {"o":0.69,"h":0.78,"l":0.68,"c":0.77,"bullish":True},
            {"o":0.79,"h":0.80,"l":0.58,"c":0.59,"bullish":False,"highlight":True},
        ],
        "support_level": None,
        "zone": (0.76, 0.80),
        "annotations": [
            {"candle_idx":4,"point":"body_mid","side":"left","text":"被吞噬","color":GREEN},
            {"candle_idx":5,"point":"low",     "side":"right","text":"完全吞噬","color":RED},
        ],
        "points": [
            "紅色實體完全包住前一根綠色實體",
            "出現在高點 + 壓力區更可靠",
            "ICT：常出現在 Breaker Block 附近",
            "代表機構在高位大量出貨",
        ],
    },
    "doji": {
        "title":        "十字星（Doji）",
        "signal":       "市場猶豫轉折",
        "signal_color": "black",
        "candles": [
            {"o":0.78,"h":0.80,"l":0.70,"c":0.71,"bullish":False},
            {"o":0.71,"h":0.73,"l":0.63,"c":0.64,"bullish":False},
            {"o":0.64,"h":0.66,"l":0.56,"c":0.57,"bullish":False},
            {"o":0.57,"h":0.59,"l":0.49,"c":0.50,"bullish":False},
            {"o":0.50,"h":0.59,"l":0.41,"c":0.50,"bullish":True,"highlight":True},
            {"o":0.50,"h":0.62,"l":0.49,"c":0.61,"bullish":True},
        ],
        "support_level": 0.45,
        "zone": None,
        "annotations": [
            {"candle_idx":4,"point":"high","side":"right","text":"上影=下影","color":BLACK},
            {"candle_idx":4,"point":"low", "side":"right","text":"多空平衡",  "color":GREY},
        ],
        "points": [
            "開盤價 ≈ 收盤價，實體幾乎為零",
            "上下影線相近代表多空膠著",
            "單獨出現不夠，需看後一根確認",
            "出現在關鍵支撐 / 壓力位才有意義",
        ],
    },
    "morning_star": {
        "title":        "晨星（Morning Star）",
        "signal":       "三K線看多反轉",
        "signal_color": "green",
        "candles": [
            {"o":0.85,"h":0.87,"l":0.77,"c":0.78,"bullish":False},
            {"o":0.78,"h":0.80,"l":0.70,"c":0.71,"bullish":False},
            {"o":0.71,"h":0.73,"l":0.63,"c":0.64,"bullish":False},
            {"o":0.64,"h":0.65,"l":0.52,"c":0.53,"bullish":False},
            {"o":0.51,"h":0.54,"l":0.45,"c":0.52,"bullish":True, "highlight":False},
            {"o":0.52,"h":0.74,"l":0.51,"c":0.73,"bullish":True, "highlight":True},
        ],
        "support_level": 0.48,
        "zone": (0.51, 0.57),
        "annotations": [
            {"candle_idx":3,"point":"body_mid","side":"left","text":"大陰線","color":RED},
            {"candle_idx":4,"point":"low",     "side":"right","text":"星星","color":BLACK},
            {"candle_idx":5,"point":"high",    "side":"right","text":"大陽線","color":GREEN},
        ],
        "points": [
            "第一根：長陰線，賣壓強烈",
            "第二根：小星星，市場猶豫（可為十字星）",
            "第三根：大陽線，需收回第一根實體 50%+",
            "三根組合缺一不可，配合成交量更準",
        ],
    },
}


# ── 幻燈片生成 ───────────────────────────────────────────────────────────────────

def _slide_pattern(pattern_key: str, slide_num: int = 1) -> Image.Image:
    """K 線形態教學張：上方示意圖 + 下方重點解說"""
    p = KLINE_PATTERNS[pattern_key]
    img, draw = _canvas()

    draw.line([(0, 0), (W, 0)], fill=GREEN, width=8)

    # 頁碼
    draw.text((54, 42), f"{slide_num:02d}", font=fb(52), fill=CREAM2)

    # 標題
    title_lines = _wrap(draw, p["title"], fb(68), W - 108)
    ty = 110
    for line in title_lines[:2]:
        draw.text((54, ty), line, font=fb(68), fill=BLACK)
        ty += 84

    # 信號 badge
    sig_color = GREEN if p["signal_color"] == "green" else (RED if p["signal_color"] == "red" else BLACK)
    sig_fnt = fb(34)
    bb = draw.textbbox((0,0), p["signal"], font=sig_fnt)
    sw = bb[2] - bb[0]
    draw.rounded_rectangle([54, ty, 54 + sw + 32, ty + 48],
                            radius=8, fill=sig_color)
    draw.text((70, ty + 8), p["signal"], font=sig_fnt, fill=WHITE)
    ty += 64

    # 蠟燭示意圖區域
    diagram_y = ty + 8
    diagram_h = 360
    draw = _draw_pattern_area(img, draw, p["candles"],
                       ax=54, ay=diagram_y, aw=W-108, ah=diagram_h,
                       support_level=p.get("support_level"),
                       zone=p.get("zone"),
                       annotations=p.get("annotations"))

    # 重點解說
    py = diagram_y + diagram_h + 28
    for pt in p["points"][:4]:
        draw.ellipse([54, py+14, 70, py+30], fill=GREEN)
        pt_lines = _wrap(draw, pt, fr(44), W - 120)
        lpy = py
        for l in pt_lines[:2]:
            draw.text((88, lpy), l, font=fr(44), fill=BLACK)
            lpy += 56
        py = lpy + 14

    _brand(draw)
    return img


def _slide_cover_kline(patterns: list) -> Image.Image:
    """K 線形態系列封面"""
    img, draw = _canvas()
    draw.line([(0, 0), (W, 0)], fill=GREEN, width=8)

    draw.text((54, 80),  "K線形態",     font=fb(110), fill=BLACK)
    draw.text((54, 208), "看懂這幾根",  font=fb(96),  fill=BLACK)
    draw.text((54, 320), "多空一目瞭然", font=fb(88),  fill=GREEN)

    draw.line([(54, 436), (W-54, 436)], fill=CREAM2, width=2)

    # 預覽小圖：畫幾根示意蠟燭
    preview_candles = [
        {"o":0.5,"h":0.9,"l":0.45,"c":0.85,"bullish":True},
        {"o":0.85,"h":0.88,"l":0.60,"c":0.62,"bullish":False},
        {"o":0.62,"h":0.64,"l":0.30,"c":0.61,"bullish":True,"highlight":True},
        {"o":0.61,"h":0.80,"l":0.60,"c":0.78,"bullish":True},
    ]
    _draw_pattern_area(img, draw, preview_candles,
                       ax=54, ay=460, aw=W-108, ah=300,
                       support_level=0.35, zone=None, annotations=[])

    # 本篇含哪些形態
    py = 790
    for name in patterns[:3]:
        p = KLINE_PATTERNS.get(name, {})
        title = p.get("title", name)
        bb = draw.textbbox((0,0), "▶", font=fb(36))
        draw.text((54, py), "▶", font=fb(36), fill=GREEN)
        draw.text((100, py), title, font=fr(42), fill=BLACK)
        py += 60

    _brand(draw)
    return img


def _slide_cta_kline() -> Image.Image:
    """CTA 頁（共用 ict_post_gen 的 3-step 版）"""
    from ict_post_gen import _slide_cta
    return _slide_cta("K線形態")


# ── 主入口 ────────────────────────────────────────────────────────────────────

def generate_kline_post(pattern_keys: list = None) -> tuple:
    """
    生成 K 線形態教學輪播。
    pattern_keys: 指定形態清單，預設用 hammer/bullish_engulfing/shooting_star
    回傳 (slides: list[PIL.Image], caption: str)
    """
    if pattern_keys is None:
        pattern_keys = ["hammer", "shooting_star", "bullish_engulfing"]

    slides = []

    # 封面
    slides.append(_slide_cover_kline(pattern_keys))

    # 每個形態一張
    for i, key in enumerate(pattern_keys):
        if key in KLINE_PATTERNS:
            slides.append(_slide_pattern(key, slide_num=i+1))

    # CTA
    slides.append(_slide_cta_kline())

    # 產生文案
    names = "、".join(KLINE_PATTERNS[k]["title"] for k in pattern_keys if k in KLINE_PATTERNS)
    caption = (
        f"K線形態看懂了嗎？\n\n"
        f"本篇教學涵蓋：{names}\n\n"
        f"這幾個形態配合 ICT 聰明錢理論使用效果加倍，\n"
        f"機構都在這些位置留下腳印！\n\n"
        f"WycBotAI AI 每日自動掃描 K 線信號，\n"
        f"讓你不再靠感覺，用邏輯交易。\n\n"
        f"💬 留言「K線」取得完整形態手冊\n\n"
        f"#K線形態 #技術分析 #加密貨幣 #ICT策略 #WycBotAI #聰明錢"
    )
    return slides, caption


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    keys = sys.argv[1:] if len(sys.argv) > 1 else None
    slides, caption = generate_kline_post(keys)
    out = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out, exist_ok=True)
    for i, s in enumerate(slides):
        path = os.path.join(out, f"kline_preview_{i+1}.jpg")
        s.save(path, quality=95)
        print(f"  saved: {path}")
    print(f"\nCaption:\n{caption}")
    print(f"\n可用形態：{list(KLINE_PATTERNS.keys())}")
