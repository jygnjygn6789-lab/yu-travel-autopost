"""
ICT 聰明錢風格輪播生成器
仿照 @1336cryptoclub 米白簡潔版面，加入 WycBotAI 元素 + BingX CTA
"""
import os, re, json
import anthropic
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from font_paths import FONT_BOLD, FONT_REG

W, H     = 1080, 1080
BG       = (245, 241, 232)   # 封面米白底（同 @1336cryptoclub）
BG_GREY  = (238, 238, 238)   # 內容頁淺灰底
BLACK    = (18,  18,  18)
GREY     = (110, 110, 110)
GREEN    = (0,   180, 100)   # WycBotAI 綠
RED      = (210,  45,  45)
DARK     = (28,  28,  28)
CREAM2   = (235, 230, 218)

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


# ── K 線示意圖 ────────────────────────────────────────────────────────────────

def _ema(prices, period=9):
    k, result = 2 / (period + 1), []
    prev = None
    for p in prices:
        if prev is None:
            prev = p
        prev = p * k + prev * (1 - k)
        result.append(prev)
    return result


def _draw_kline(draw, x1, y1, x2, y2, chart_type="uptrend", bg_color=BG_GREY):
    """在 (x1,y1)-(x2,y2) 區域畫 K 線示意圖"""
    import math, random
    random.seed(42)

    W_c = x2 - x1
    H_c = y2 - y1
    N = 22

    # ── 依 chart_type 生成收盤價序列 ──
    def gen(base, drift, vol, n=N):
        prices, p = [], base
        for _ in range(n):
            p += drift + random.uniform(-vol, vol)
            prices.append(max(p, base * 0.5))
        return prices

    if chart_type == "uptrend":
        closes = gen(100, 1.5, 2)
    elif chart_type == "downtrend":
        closes = gen(140, -1.5, 2)
    elif chart_type == "support_bounce":
        closes = gen(100, 0.5, 3)
        mid = N // 2
        for i in range(mid - 3, mid + 2):
            closes[i] -= 10
    elif chart_type == "resistance":
        closes = gen(100, 0.3, 2)
        for i in range(N // 2, N // 2 + 4):
            closes[i] = min(closes[i], closes[N // 2 - 1] + 5)
    elif chart_type == "golden_cross":
        closes = gen(90, 2, 2.5)
        closes[:N//3] = [90 - i * 0.5 for i in range(N//3)]
    elif chart_type == "death_cross":
        closes = gen(130, -2, 2.5)
        closes[:N//3] = [130 + i * 0.5 for i in range(N//3)]
    elif chart_type == "triple_ema":
        closes = gen(100, 1.2, 1.5)
    elif chart_type == "compression":
        closes = [100 + math.sin(i * 0.5) * (8 - i * 0.2) for i in range(N)]
    elif chart_type == "bollinger_bands":
        closes = gen(100, 0.3, 3)  # 橫盤震盪，帶上下穿越
    else:
        closes = gen(100, 1, 2)

    # 生成 OHLC
    candles = []
    for i, c in enumerate(closes):
        o = closes[i - 1] if i > 0 else c
        hi = max(o, c) + random.uniform(0.5, 2)
        lo = min(o, c) - random.uniform(0.5, 2)
        candles.append((o, hi, lo, c))

    mn = min(c[2] for c in candles)
    mx = max(c[1] for c in candles)
    rng = max(mx - mn, 1)

    PAD = 16
    def sy(v):
        return y2 - PAD - int((v - mn) / rng * (H_c - PAD * 2))

    cw = max(4, W_c // (N * 2))
    step = W_c // N

    # ── 畫蠟燭 ──
    for i, (o, hi, lo, c) in enumerate(candles):
        cx = x1 + i * step + step // 2
        col = GREEN if c >= o else RED
        draw.line([(cx, sy(hi)), (cx, sy(lo))], fill=col, width=1)
        body_t, body_b = sy(max(o, c)), sy(min(o, c))
        if body_b - body_t < 2:
            body_b = body_t + 3
        draw.rectangle([cx - cw, body_t, cx + cw, body_b], fill=col)

    # ── 畫 EMA 線（bollinger_bands 不畫 EMA，避免與帶線混淆）──
    if chart_type != "bollinger_bands":
        ema9  = _ema(closes, 9)
        ema21 = _ema(closes, 21)
        if chart_type == "triple_ema":
            # 三條均線：短/中/長，粗線、顏色明顯區分
            ema7  = _ema(closes, 7)
            ema14 = _ema(closes, 14)
            ema_long = _ema(closes, min(20, N - 1))
            ema_lines = [
                (ema7,    (220,  50,  50), 4),   # 紅色短線（最靈敏）
                (ema14,   (220, 160,   0), 3),   # 橘色中線
                (ema_long,(40,  120, 220), 3),   # 藍色長線（最穩）
            ]
        elif chart_type in ("golden_cross", "death_cross"):
            ema_lines = [
                (ema9,  (220,  50,  50), 3),
                (ema21, (40,  120, 220), 3),
            ]
        elif chart_type == "compression":
            ema_lines = [
                (ema9,  (0, 160, 80),  2),
                (ema21, (220, 140, 0), 2),
            ]
        else:
            ema_lines = [(ema9, (0, 160, 80), 2)]

        for ema_vals, col, lw in ema_lines:
            pts = [(x1 + i * step + step // 2, sy(v)) for i, v in enumerate(ema_vals)]
            for j in range(1, len(pts)):
                draw.line([pts[j-1], pts[j]], fill=col, width=lw)

        # golden_cross / death_cross：在交叉點畫明顯圓圈標記
        if chart_type in ("golden_cross", "death_cross"):
            e9  = _ema(closes, 9)
            e21 = _ema(closes, 21)
            for i in range(1, len(e9)):
                prev_diff = e9[i-1] - e21[i-1]
                curr_diff = e9[i]   - e21[i]
                if prev_diff * curr_diff < 0:  # 穿越點
                    cx = x1 + i * step + step // 2
                    cy = sy((e9[i] + e21[i]) / 2)
                    r = 10
                    cross_col = GREEN if chart_type == "golden_cross" else RED
                    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                                 outline=cross_col, width=3)
                    break

    # ── 布林帶（上中下三條 + 帶內填色）──
    if chart_type == "bollinger_bands":
        period = 14
        std_mult = 2.0
        bb_mid, bb_upper, bb_lower = [], [], []
        for i in range(len(closes)):
            window = closes[max(0, i - period + 1): i + 1]
            avg = sum(window) / len(window)
            variance = sum((v - avg) ** 2 for v in window) / len(window)
            std = variance ** 0.5
            bb_mid.append(avg)
            bb_upper.append(avg + std_mult * std)
            bb_lower.append(avg - std_mult * std)

        # 先用 RGBA 合成帶內填色（淡藍底色）
        from PIL import Image as _PILImg
        overlay = _PILImg.new("RGBA", (x2 - x1, y2 - y1), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        fill_pts = (
            [(i * step + step // 2, sy(v) - y1) for i, v in enumerate(bb_upper)]
            + [(i * step + step // 2, sy(v) - y1) for i, v in reversed(list(enumerate(bb_lower)))]
        )
        if len(fill_pts) >= 3:
            ov_draw.polygon(fill_pts, fill=(100, 160, 255, 55))
        base_rgba = draw._image.convert("RGBA") if hasattr(draw, "_image") else None
        # fallback: 直接畫淡色梯形條模擬帶填色
        for i in range(len(bb_upper) - 1):
            draw.polygon([
                (x1 + i * step + step // 2,       sy(bb_upper[i])),
                (x1 + (i+1) * step + step // 2,   sy(bb_upper[i+1])),
                (x1 + (i+1) * step + step // 2,   sy(bb_lower[i+1])),
                (x1 + i * step + step // 2,        sy(bb_lower[i])),
            ], fill=(210, 225, 245))  # 淡藍填色

        # 重新畫蠟燭（蓋住填色）
        for i, (o, hi, lo, c) in enumerate(candles):
            cx = x1 + i * step + step // 2
            col = GREEN if c >= o else RED
            draw.line([(cx, sy(hi)), (cx, sy(lo))], fill=col, width=1)
            body_t, body_b = sy(max(o, c)), sy(min(o, c))
            if body_b - body_t < 2:
                body_b = body_t + 3
            draw.rectangle([cx - cw, body_t, cx + cw, body_b], fill=col)

        # 畫三條帶線（粗 + 顏色對比）
        for band, col, lw in [
            (bb_upper, (200, 100, 0), 3),    # 橘紅上帶
            (bb_mid,   (60,  60, 180), 3),   # 深藍中線
            (bb_lower, (200, 100, 0), 3),    # 橘紅下帶
        ]:
            pts = [(x1 + i * step + step // 2, sy(v)) for i, v in enumerate(band)]
            for j in range(1, len(pts)):
                draw.line([pts[j-1], pts[j]], fill=col, width=lw)

    # ── 水平支撐/阻力虛線 ──
    if chart_type in ("support_bounce", "resistance"):
        level_y = sy(sorted(closes)[N // 2])
        for dx in range(x1, x2, 12):
            draw.line([(dx, level_y), (dx + 6, level_y)],
                      fill=(160, 160, 160), width=1)


def _brand(draw, dark_mode=False):
    """底部品牌：IG圖示 + WYCBOTAI2026（仿 @1336cryptoclub 浮水印）"""
    color = (160, 160, 160) if dark_mode else (140, 140, 140)
    handle = "WYCBOTAI2026"
    font = fr(28)

    bb = draw.textbbox((0, 0), handle, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]

    icon_sz = 34
    gap = 10
    total_w = icon_sz + gap + tw
    sx = (W - total_w) // 2
    cy = H - 52

    # ── IG 相機圖示（外框 + 圓 + 小點）──
    draw.rounded_rectangle(
        [sx, cy - icon_sz // 2, sx + icon_sz, cy + icon_sz // 2],
        radius=8, outline=color, width=2
    )
    cr = icon_sz // 4 - 1
    draw.ellipse(
        [sx + icon_sz//2 - cr, cy - cr, sx + icon_sz//2 + cr, cy + cr],
        outline=color, width=2
    )
    dot = 4
    draw.ellipse(
        [sx + icon_sz - dot*2 - 2, cy - icon_sz//2 + 4,
         sx + icon_sz - dot - 2, cy - icon_sz//2 + 4 + dot],
        fill=color
    )

    # ── 文字 ──
    tx = sx + icon_sz + gap
    ty = cy - th // 2 - 1
    draw.text((tx, ty), handle, font=font, fill=color)


def _accent_bar(draw, x=54, y=None, w=120, color=GREEN, thickness=6):
    if y is not None:
        draw.line([(x, y), (x + w, y)], fill=color, width=thickness)


# ── 1. 封面 ───────────────────────────────────────────────────────────────────

def _slide_cover(topic: str, hook: str, sub: str) -> Image.Image:
    img, draw = _canvas()

    # 主標題（粗體，置中）
    title_fnt = fb(68)
    lines = _wrap(draw, hook, title_fnt, W - 108)
    total_h = len(lines[:3]) * 88
    y = (H - total_h) // 2 - 120
    for line in lines[:3]:
        bb = draw.textbbox((0, 0), line, font=title_fnt)
        tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, y), line, font=title_fnt, fill=BLACK)
        y += 88

    # 副標題（紅色，置中）
    sub_fnt = fb(52)
    sub_lines = _wrap(draw, sub, sub_fnt, W - 108)
    sy = y + 48
    for line in sub_lines[:2]:
        bb = draw.textbbox((0, 0), line, font=sub_fnt)
        tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, sy), line, font=sub_fnt, fill=RED)
        sy += 66

    _brand(draw)
    return img


# ── 內容頁（問題 + 答案）─────────────────────────────────────────────────────

def _draw_centered(draw, text, font, y, color, max_w=W - 108):
    """單行文字置中繪製"""
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    x = (W - min(tw, max_w)) // 2
    draw.text((x, y), text, font=font, fill=color)
    return bb[3] - bb[1]  # 回傳行高


def _slide_qa(question: str, answer_lines: list, slide_num: int,
              highlight: str = "", color=BLACK,
              chart_type: str = "uptrend") -> Image.Image:
    """內容頁：淺灰底、置中、字體仿 @1336cryptoclub 大小 + K 線示意圖"""
    img = Image.new("RGB", (W, H), BG_GREY)
    draw = ImageDraw.Draw(img)

    # 標題（粗體，置中）
    title_fnt = fb(46)
    q_lines = _wrap(draw, question, title_fnt, W - 120)
    y = 110
    for line in q_lines[:3]:
        _draw_centered(draw, line, title_fnt, y, color)
        y += 60

    y += 24

    # Highlight box（若有，置中）
    if highlight:
        hl_lines = _wrap(draw, highlight, fb(42), W - 160)
        box_h = len(hl_lines) * 56 + 28
        draw.rounded_rectangle([54, y, W - 54, y + box_h],
                                radius=10, fill=DARK)
        hy = y + 14
        for hl in hl_lines:
            bb = draw.textbbox((0, 0), hl, font=fb(42))
            tw = bb[2] - bb[0]
            draw.text(((W - tw) // 2, hy), hl, font=fb(42), fill=(255, 255, 255))
            hy += 56
        y = y + box_h + 28

    # 答案條列（置中，細字）
    body_fnt = fr(36)
    for ans in answer_lines[:5]:
        ans_lines = _wrap(draw, ans, body_fnt, W - 120)
        for al in ans_lines[:3]:
            _draw_centered(draw, al, body_fnt, y, BLACK)
            y += 48
        y += 14

    # ── K 線示意圖（文字下方空白區）──
    chart_top = max(y + 24, 580)
    chart_bot = H - 90
    if chart_bot - chart_top > 120:
        _draw_kline(draw, 60, chart_top, W - 60, chart_bot, chart_type, BG_GREY)

    _brand(draw)
    return img


# ── WycBotAI 專屬頁（暗色）──────────────────────────────────────────────────

def _slide_wycbotai(feature_title: str, points: list) -> Image.Image:
    """暗色背景的 WycBotAI AI 功能介紹頁"""
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)

    # 頂部 accent
    draw.line([(0, 0), (W, 0)], fill=GREEN, width=8)

    # WycBotAI 標籤
    draw.text((54, 48), "WycBotAI", font=fb(48), fill=GREEN)
    draw.line([(54, 108), (W - 54, 108)], fill=(60, 60, 60), width=1)

    # 標題
    title_lines = _wrap(draw, feature_title, fb(80), W - 108)
    y = 140
    for line in title_lines[:3]:
        draw.text((54, y), line, font=fb(80), fill=(255, 255, 255))
        y += 100

    # 功能點（卡片）
    y += 24
    for pt in points[:4]:
        pt_lines = _wrap(draw, pt, fr(48), W - 200)
        card_h = max(90, len(pt_lines) * 60 + 30)
        draw.rounded_rectangle([54, y, W - 54, y + card_h],
                                radius=10, fill=(45, 45, 45))
        # 綠色左邊條
        draw.rounded_rectangle([54, y, 66, y + card_h], radius=4, fill=GREEN)
        py = y + (card_h - len(pt_lines) * 60) // 2
        for pl in pt_lines[:2]:
            draw.text((86, py), pl, font=fr(48), fill=(220, 220, 220))
            py += 60
        y += card_h + 18

    _brand(draw, dark_mode=True)
    return img


# ── 最後一張：IG 主頁截圖 + CTA（同 @1336cryptoclub 最後一張）───────────────

def _slide_last(profile_screenshot_path: str = None, indicator_short: str = "EMA") -> Image.Image:
    """
    最後一張：放 wycbotai IG 主頁截圖 + 引導文字
    profile_screenshot_path: 可選，傳入主頁截圖路徑
    indicator_short: 指標縮寫，用於「留言「XXX」」CTA
    """
    img = Image.new("RGB", (W, H), BG_GREY)
    draw = ImageDraw.Draw(img)

    if profile_screenshot_path and os.path.exists(profile_screenshot_path):
        prof = Image.open(profile_screenshot_path).convert("RGB")
        # 縮放至適當大小放在中上方
        max_w, max_h = W - 80, 700
        ratio = min(max_w / prof.width, max_h / prof.height)
        new_w, new_h = int(prof.width * ratio), int(prof.height * ratio)
        prof = prof.resize((new_w, new_h), Image.LANCZOS)
        x_off = (W - new_w) // 2
        img.paste(prof, (x_off, 60))
        y_text = 60 + new_h + 40
    else:
        y_text = 320

    # 引導文字（置中）
    for line, fnt, col, dy in [
        ("有用就點讚收藏", fb(52), BLACK, 0),
        (f"留言「{indicator_short}」", fb(64), RED, 72),
        ("我傳每日信號給你", fb(52), BLACK, 152),
    ]:
        bb = draw.textbbox((0, 0), line, font=fnt)
        draw.text(((W - (bb[2]-bb[0])) // 2, y_text + dy), line, font=fnt, fill=col)

    _brand(draw)
    return img


# ── CTA 頁（BingX + WycBotAI）──────────────────────────────────────────────

def _slide_cta(indicator_topic: str) -> Image.Image:
    img, draw = _canvas()

    draw.line([(0, 0), (W, 0)], fill=GREEN, width=8)

    # 標題
    draw.text((54, 60), "學完了？",   font=fb(80), fill=BLACK)
    draw.text((54, 158), "馬上行動！", font=fb(80), fill=GREEN)
    draw.line([(54, 258), (W - 54, 258)], fill=CREAM2, width=2)

    # 三個步驟
    steps = [
        {
            "num": "01",
            "icon_color": GREEN,
            "title": "按讚 + 追蹤 @wycbotai2026",
            "desc":  "每天學一個聰明錢概念",
        },
        {
            "num": "02",
            "icon_color": (50, 140, 220),
            "title": "點主頁連結 → 免費試用",
            "desc":  "WycBotAI AI 信號 wycbotai.com",
        },
        {
            "num": "03",
            "icon_color": (220, 160, 30),
            "title": "BingX 輸入邀請碼 LKUUM8",
            "desc":  "完成註冊 → 免費送1個月專業版",
        },
    ]

    y = 282
    for step in steps:
        c = step["icon_color"]
        card_h = 192
        draw.rounded_rectangle([54, y, W - 54, y + card_h], radius=16, fill=(235, 230, 218))

        # 數字圓圈
        cx, cy = 54 + 52, y + card_h // 2
        draw.ellipse([cx - 38, cy - 38, cx + 38, cy + 38], fill=c)
        bb_n = draw.textbbox((0, 0), step["num"], font=fb(38))
        draw.text((cx - (bb_n[2]-bb_n[0])//2, cy - (bb_n[3]-bb_n[1])//2 - 2),
                  step["num"], font=fb(38), fill=(255, 255, 255))

        # 文字
        draw.text((148, y + 44),  step["title"], font=fb(46), fill=BLACK)
        draw.text((148, y + 108), step["desc"],  font=fr(38), fill=GREY)
        y += card_h + 18

    _brand(draw)
    return img


# ── Claude 腳本生成 ─────────────────────────────────────────────────────────

def _generate_script(topic: str) -> dict:
    client = anthropic.Anthropic()
    prompt = f"""你是加密貨幣 ICT/聰明錢策略教育創作者，為 WycBotAI IG 帳號生成「{topic}」教學輪播腳本。

風格參考：@1336cryptoclub
- 用反問句吸引人：先說出新手的錯誤想法，再給正確答案
- 語言直接有力，像交易員在說話
- 每張只有 1-2 個核心概念，不堆砌
- 繁體中文

嚴格回傳 JSON，不要多餘文字：
{{
  "topic_short": "主題縮寫（如 Fib、EMA、OB）",
  "hook": "封面大標題，反問或震撼句（25字以內）",
  "sub": "封面副標題，補充說明（20字以內）",
  "slides": [
    {{
      "question": "這張的核心問題/標題（20字以內）",
      "highlight": "最重要的一句話，放在醒目框裡（20字以內，可留空）",
      "answers": ["答案重點1（25字以內）", "答案重點2", "答案重點3"],
      "color": "black",
      "chart_type": "uptrend|downtrend|support_bounce|resistance|golden_cross|death_cross|triple_ema|compression|bollinger_bands"
    }}
  ],
  "wycbotai_title": "WycBotAI 功能頁標題（25字以內）",
  "wycbotai_points": ["AI功能點1（20字以內）", "AI功能點2", "AI功能點3", "AI功能點4"],
  "caption": "IG 文案（繁中，120-180字，含3-5個hashtag）"
}}

slides 要有 3-4 張，涵蓋：基本概念、為什麼新手犯錯、正確用法。

重要：每張 slide 的 chart_type 必須配合該張「講的概念」來選，不能全部用同一種：
- 講趨勢/做多 → uptrend
- 講下跌/做空 → downtrend
- 講支撐反彈/Fibonacci 進場 → support_bounce
- 講阻力/壓力位 → resistance
- 講黃金交叉/MACD 轉多 → golden_cross
- 講死亡交叉/MACD 轉空 → death_cross
- 講多條均線排列/三線多頭 → triple_ema
- 講橫盤收縮/波動率縮小 → compression
- 講布林帶/標準差通道 → bollinger_bands
每張 slide 依照它自己的概念選最合適的 chart_type，不同 slide 要盡量不重複。"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group())
    except Exception:
        cleaned = re.sub(r',\s*([}\]])', r'\1', m.group())
        return json.loads(cleaned)


# ── 主入口 ──────────────────────────────────────────────────────────────────

def generate_ict_post(topic: str = "斐波那契回調（Fibonacci Retracement）",
                      profile_screenshot: str = None) -> tuple:
    """
    生成 ICT 聰明錢風格輪播（仿 @1336cryptoclub）
    profile_screenshot: 可選，wycbotai IG 主頁截圖路徑（用於最後一張）
    回傳 (slides: list[PIL.Image], caption: str)
    """
    print(f"[ICT] 生成「{topic}」腳本...")
    data = _generate_script(topic)
    if not data:
        raise RuntimeError("Claude 腳本生成失敗")

    slides = []

    # 1. 封面
    slides.append(_slide_cover(
        topic=data.get("topic_short", topic.split("（")[0]),
        hook=data.get("hook", f"你真的會用{topic}嗎？"),
        sub=data.get("sub", "聰明錢都在這裡進場")
    ))

    # 2-N. 內容頁
    for i, slide in enumerate(data.get("slides", [])[:4]):
        color_name = slide.get("color", "black")
        color = RED if color_name == "red" else BLACK
        ct = slide.get("chart_type", "uptrend")
        slides.append(_slide_qa(
            question=slide.get("question", ""),
            answer_lines=slide.get("answers", []),
            slide_num=i + 1,
            highlight=slide.get("highlight", ""),
            color=color,
            chart_type=ct,
        ))

    # WycBotAI 功能頁（暗色）
    slides.append(_slide_wycbotai(
        feature_title=data.get("wycbotai_title", "AI 幫你自動找這些位置"),
        points=data.get("wycbotai_points", [
            "AI 每日掃描 Fib 關鍵回調位",
            "自動標記 0.618-0.786 黃金區間",
            "結合成交量確認進場強度",
            "止損止盈比例自動計算",
        ])
    ))

    # 最後一張：IG 主頁截圖 CTA（同 @1336cryptoclub）
    topic_short = data.get("topic_short", topic.split("（")[0])
    slides.append(_slide_last(profile_screenshot, indicator_short=topic_short))

    caption = data.get("caption", f"#{topic.split('（')[0]} #加密貨幣 #技術分析 #WycBotAI #聰明錢")
    print(f"[ICT] 生成完成，共 {len(slides)} 張")
    return slides, caption


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    topic = sys.argv[1] if len(sys.argv) > 1 else "斐波那契回調（Fibonacci Retracement）"
    slides, caption = generate_ict_post(topic)
    out = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out, exist_ok=True)
    for i, s in enumerate(slides):
        path = os.path.join(out, f"ict_preview_{i+1}.jpg")
        s.save(path, quality=95)
        print(f"  saved: {path}")
    print(f"\nCaption:\n{caption}")
