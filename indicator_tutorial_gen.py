"""
每日技術指標教學輪播生成器 - WycBotAI Dark Premium Style
6 張輪播：封面 / 定義 / K線圖 / 信號判讀 / 常見錯誤 / CTA
"""
import os, re, json, datetime
import anthropic
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

from font_paths import FONT_BOLD, FONT_REG
from chart_gen import get_chart

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

def fb(s): return ImageFont.truetype(FONT_BOLD, s)
def fr(s): return ImageFont.truetype(FONT_REG,  s)

W, H  = 1080, 1350
BG    = (8,  13,  30)
GREEN = (0,  255, 136)
GOLD  = (255, 215,  0)
RED   = (255,  68, 68)
WHITE = (255, 255, 255)
GREY  = (136, 153, 170)
DIM   = (22,  33,  58)

# ── 每日指標循環表 ─────────────────────────────────────────────────────────────
INDICATORS = [
    "EMA（指數移動平均線）",
    "RSI（相對強弱指標）",
    "MACD（移動平均收斂發散指標）",
    "布林帶（Bollinger Bands）",
    "成交量分析（Volume）",
    "KD指標（隨機振盪指標）",
    "ADX（平均趨向指標）",
    "支撐位與壓力位",
    "K線形態：錘子線與流星線",
    "K線形態：吞噬形態（看多/看空）",
    "斐波那契回調",
    "均線多頭/空頭排列",
    "止損與止盈設定技巧",
    "資金管理與倉位計算",
]


def get_today_indicator() -> str:
    day = datetime.date.today().timetuple().tm_yday
    return INDICATORS[day % len(INDICATORS)]


# ── 共用繪圖工具 ───────────────────────────────────────────────────────────────

def _canvas():
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    # subtle dot grid
    for x in range(60, W, 108):
        for y in range(60, H, 108):
            draw.ellipse([x-1, y-1, x+1, y+1], fill=(255, 255, 255, 6))
    return img, ImageDraw.Draw(img)


def _brand(draw):
    draw.line([(0, H - 88), (W, H - 88)], fill=(*GREEN, 25), width=1)
    draw.text((54,      H - 66), "@wycbotai",    font=fr(28), fill=(*GREY,  180))
    draw.text((W - 260, H - 66), "wycbotai.com", font=fr(28), fill=(*GREEN, 160))


def _tag(draw, text, y=52):
    fnt = fb(28)
    bb  = draw.textbbox((0, 0), text, font=fnt)
    tw  = bb[2] - bb[0]; th = bb[3] - bb[1]
    px, py = 18, 8
    draw.rounded_rectangle(
        [54, y, 54 + tw + px*2, y + th + py*2],
        radius=6, fill=DIM, outline=(*GREEN, 100), width=1
    )
    draw.text((54 + px, y + py), text, font=fnt, fill=GREEN)


def _wrap(draw, text, font, max_w):
    words, lines, cur = list(text), [], ""
    for ch in text:
        test = cur + ch
        bb   = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


# ── 6 張 Slide ────────────────────────────────────────────────────────────────

def _slide_cover(data: dict) -> Image.Image:
    img, draw = _canvas()
    draw.line([(54, 132), (W - 54, 132)], fill=(*GREEN, 30), width=1)

    # hook
    hook = data.get("hook", "你真的懂這個指標嗎？")
    lines = _wrap(draw, hook, fb(64), W - 108)
    y = 170
    for line in lines[:3]:
        draw.text((54, y), line, font=fb(64), fill=WHITE)
        y += 82

    # indicator name (big green)
    short = data.get("indicator_short", "EMA")
    draw.text((54, y + 20), short, font=fb(180), fill=GREEN)
    y += 220

    # full name
    full = data.get("indicator_full", "")
    if full:
        draw.text((54, y), full, font=fr(44), fill=GREY)

    draw.line([(54, H - 228), (W - 54, H - 228)], fill=(*GREEN, 30), width=1)
    draw.text((54, H - 200), "往下滑學會這個指標  v", font=fb(40), fill=(*GOLD, 220))
    _brand(draw)
    return img


def _slide_definition(data: dict) -> Image.Image:
    img, draw = _canvas()
    draw.text((W - 280, 28), "01", font=fb(160), fill=(*GREEN, 14))

    title = data.get("indicator_short", "EMA") + " 是什麼？"
    draw.text((54, 190), title, font=fb(82), fill=WHITE)
    draw.line([(54, 290), (600, 290)], fill=GREEN, width=4)

    wi = data.get("what_is_it", {})
    headline  = wi.get("headline",  "這個指標幫助你判斷趨勢方向")
    highlight = wi.get("highlight", "")
    bullets   = wi.get("bullets",   [])

    if highlight:
        by = 316
        draw.rounded_rectangle([54, by, W - 54, by + 92], radius=12, fill=DIM)
        draw.rounded_rectangle([54, by, 64,     by + 92], radius=4,  fill=GREEN)
        draw.text((88, by + 26), highlight, font=fb(38), fill=GREEN)
        y = by + 112
    else:
        draw.text((54, 316), headline, font=fr(44), fill=GREY)
        y = 380

    for bullet in bullets[:5]:
        draw.ellipse([54, y + 14, 68, y + 28], fill=GREEN)
        lines = _wrap(draw, bullet, fr(42), W - 120)
        for line in lines[:2]:
            draw.text((88, y), line, font=fr(42), fill=WHITE)
            y += 60
        y += 8

    _brand(draw)
    return img


def _slide_chart(data: dict, indicator_name: str) -> Image.Image:
    img, draw = _canvas()
    draw.text((54, 120), "實際 K 線圖解", font=fb(64), fill=WHITE)
    draw.line([(54, 204), (480, 204)], fill=GREEN, width=3)

    # chart image
    chart_h = 720
    chart   = get_chart(indicator_name, width=W - 8, height=chart_h)
    img.paste(chart, (4, 224))

    # caption below chart
    caption = data.get("chart_caption", "DOGE/USDT 4H 真實 K 線數據")
    draw    = ImageDraw.Draw(img)
    draw.text((54, 224 + chart_h + 12), caption, font=fr(34), fill=GREY)

    _brand(draw)
    return img


def _slide_signals(data: dict) -> Image.Image:
    img, draw = _canvas()
    draw.text((W - 280, 28), "02", font=fb(160), fill=(*GREEN, 14))

    draw.text((54, 190), "進場 & 出場信號", font=fb(80), fill=WHITE)
    draw.line([(54, 288), (560, 288)], fill=GREEN, width=4)

    signals = data.get("signals", {})

    # BUY signals
    buy_list = signals.get("buy", [])
    draw.rounded_rectangle([54, 316, W - 54, 356], radius=8, fill=DIM)
    draw.rounded_rectangle([54, 316, 64, 356], radius=4, fill=GREEN)
    draw.text((88, 324), "做多信號", font=fb(30), fill=GREEN)
    y = 372
    for item in buy_list[:3]:
        draw.ellipse([60, y + 10, 72, y + 22], fill=GREEN)
        lines = _wrap(draw, item, fr(40), W - 120)
        for line in lines[:2]:
            draw.text((88, y), line, font=fr(40), fill=WHITE)
            y += 55
        y += 6

    y += 16
    # SELL signals
    draw.rounded_rectangle([54, y, W - 54, y + 40], radius=8, fill=DIM)
    draw.rounded_rectangle([54, y, 64, y + 40], radius=4, fill=RED)
    draw.text((88, y + 8), "做空/離場信號", font=fb(30), fill=RED)
    y += 56
    for item in signals.get("sell", [])[:3]:
        draw.ellipse([60, y + 10, 72, y + 22], fill=RED)
        lines = _wrap(draw, item, fr(40), W - 120)
        for line in lines[:2]:
            draw.text((88, y), line, font=fr(40), fill=WHITE)
            y += 55
        y += 6

    _brand(draw)
    return img


def _slide_timeframes(data: dict) -> Image.Image:
    img, draw = _canvas()
    draw.text((W - 280, 28), "03", font=fb(160), fill=(*GREEN, 14))

    draw.text((54, 190), "用對時框",   font=fb(88), fill=WHITE)
    draw.text((54, 292), "勝率直接翻倍", font=fb(76), fill=GREEN)
    draw.line([(54, 396), (560, 396)], fill=GREEN, width=4)

    tf_data = data.get("timeframes", {})
    rows = [
        ("決定方向", tf_data.get("direction", {}).get("tf", "週線 / 日線"),
                     tf_data.get("direction", {}).get("desc", "判斷主趨勢是多頭還是空頭"),
                     GREEN),
        ("尋找進場", tf_data.get("entry",     {}).get("tf", "4H / 1H"),
                     tf_data.get("entry",     {}).get("desc", "等待指標出現進場信號"),
                     GOLD),
        ("確認時機", tf_data.get("confirm",   {}).get("tf", "15分 / 30分"),
                     tf_data.get("confirm",   {}).get("desc", "觀察短線K線確認入場"),
                     (80, 180, 255)),
    ]

    y = 432
    for label, tf, desc, color in rows:
        # row card
        draw.rounded_rectangle([54, y, W - 54, y + 140], radius=14, fill=DIM)
        # left color bar
        draw.rounded_rectangle([54, y, 66, y + 140], radius=4, fill=color)
        # label
        draw.text((88, y + 14), label, font=fr(30), fill=GREY)
        # timeframe (big)
        draw.text((88, y + 50), tf, font=fb(54), fill=color)
        # desc
        desc_lines = _wrap(draw, desc, fr(36), W - 200)
        dy = y + 100
        for line in desc_lines[:1]:
            draw.text((88, dy), line, font=fr(36), fill=WHITE)
        y += 158

    # tip
    tip = tf_data.get("tip", "由大到小：先看方向，再找進場，最後確認")
    draw.line([(54, y + 8), (W - 54, y + 8)], fill=(*GREEN, 30), width=1)
    draw.text((54, y + 20), tip, font=fr(36), fill=(*GREY, 200))

    _brand(draw)
    return img


def _slide_mistakes(data: dict) -> Image.Image:
    img, draw = _canvas()
    draw.text((W - 280, 28), "04", font=fb(160), fill=(*GREEN, 14))

    draw.text((54, 190), "新手最容易",    font=fb(82), fill=WHITE)
    draw.text((54, 290), "犯的 3 個錯誤", font=fb(76), fill=RED)
    draw.line([(54, 392), (560, 392)], fill=RED, width=4)

    mistakes = data.get("mistakes", [])
    y = 424
    for i, mistake in enumerate(mistakes[:3]):
        # number circle
        nx, ny = 54, y
        draw.ellipse([nx, ny, nx + 52, ny + 52], fill=RED)
        draw.text((nx + 16, ny + 8), str(i + 1), font=fb(32), fill=WHITE)

        lines = _wrap(draw, mistake, fb(46), W - 140)
        ty = y + 2
        for line in lines[:2]:
            draw.text((120, ty), line, font=fb(46), fill=WHITE)
            ty += 60

        # sub-detail if provided in extended data
        detail = data.get("mistake_details", [None, None, None])[i]
        if detail:
            dlines = _wrap(draw, detail, fr(36), W - 140)
            for dl in dlines[:2]:
                draw.text((120, ty), dl, font=fr(36), fill=GREY)
                ty += 50

        y = max(ty, y + 140) + 24

    _brand(draw)
    return img


def _slide_cta(data: dict) -> Image.Image:
    img, draw = _canvas()
    keyword = data.get("indicator_short", "EMA")

    # Main hook
    draw.text((54, 170), "想要 AI 幫你",       font=fb(82), fill=WHITE)
    draw.text((54, 268), "自動找進場信號？",    font=fb(76), fill=WHITE)
    draw.line([(54, 372), (W - 54, 372)], fill=(*GREEN, 40), width=1)

    # Keyword CTA box
    cta_y = 400
    box_h = 152
    draw.rounded_rectangle([54, cta_y, W - 54, cta_y + box_h], radius=16, fill=DIM)
    draw.rounded_rectangle([54, cta_y, 66, cta_y + box_h], radius=4, fill=GREEN)

    # Row 1: "留言"
    draw.text((88, cta_y + 14), "留言", font=fr(38), fill=GREY)

    # Row 2: keyword pill + "我私訊免費體驗給你"
    kw_fnt = fb(64)
    bb = draw.textbbox((0, 0), keyword, font=kw_fnt)
    kw_w = bb[2] - bb[0]; kw_h = bb[3] - bb[1]
    pill_x, pill_y = 88, cta_y + 60
    draw.rounded_rectangle([pill_x, pill_y, pill_x + kw_w + 24, pill_y + kw_h + 10],
                            radius=8, fill=(0, 60, 30))
    draw.text((pill_x + 12, pill_y + 5), keyword, font=kw_fnt, fill=GREEN)

    kw_end = pill_x + kw_w + 36
    draw.text((kw_end, pill_y + 12), "我私訊免費體驗給你", font=fr(40), fill=WHITE)

    # features
    y = cta_y + box_h + 28
    features = [
        "AI 每日掃描 100+ 指標信號",
        "EMA / RSI / ADX 三重過濾",
        "自動計算止損 & 止盈比例",
    ]
    for feat in features:
        draw.text((54,  y), ">>", font=fb(40), fill=GREEN)
        draw.text((124, y), feat, font=fr(40), fill=WHITE)
        y += 68

    # CTA button
    by = H - 296
    draw.rounded_rectangle([54, by, W - 54, by + 100], radius=50, fill=GREEN)
    txt = "前往 wycbotai.com 免費體驗"
    bb2 = draw.textbbox((0, 0), txt, font=fb(42))
    draw.text(((W - (bb2[2]-bb2[0])) // 2, by + 24), txt, font=fb(42), fill=BG)

    draw.text((54, H - 164), "追蹤 @wycbotai 每日策略不錯過", font=fr(36), fill=GREY)
    _brand(draw)
    return img


# ── Claude 內容生成 ────────────────────────────────────────────────────────────

def _claude_generate(indicator_name: str) -> dict:
    client = anthropic.Anthropic()
    prompt = f"""你是加密貨幣交易教育專家，為 WycBotAI 策略網站的 Instagram 教學帳號生成貼文內容。
主題：「{indicator_name}」的新手教學輪播（Dark Premium 暗色風格）。

要求：
- 目標受眾：完全沒有技術分析基礎的新手
- 語言：繁體中文，口語化，易懂
- 不要提及任何幣種名稱，用「價格」、「K線」、「市場」等通用詞
- 每條說明 15-25 字，簡短有力

嚴格回傳以下 JSON，不要有任何多餘文字：

{{
  "hook": "一句讓新手看了想繼續看的問句（20字以內）",
  "indicator_short": "指標縮寫或簡短名稱（如 EMA、RSI）",
  "indicator_full": "指標完整中文名稱",
  "what_is_it": {{
    "headline": "一句話說明指標用途（20字以內）",
    "highlight": "最重要的一個數字/特點（20字以內）",
    "bullets": [
      "重點1（15-20字）",
      "重點2（15-20字）",
      "重點3（15-20字）",
      "重點4（15-20字）"
    ]
  }},
  "chart_caption": "圖表說明文字（25字以內，說明圖中展示了什麼）",
  "signals": {{
    "buy": [
      "做多信號1（20字以內）",
      "做多信號2（20字以內）",
      "做多信號3（20字以內）"
    ],
    "sell": [
      "做空/離場信號1（20字以內）",
      "做空/離場信號2（20字以內）",
      "做空/離場信號3（20字以內）"
    ]
  }},
  "timeframes": {{
    "direction": {{
      "tf": "週線 / 日線",
      "desc": "用這個時框判斷主趨勢方向（15-20字）"
    }},
    "entry": {{
      "tf": "4H / 1H",
      "desc": "用這個時框找進場點位（15-20字）"
    }},
    "confirm": {{
      "tf": "15分 / 30分",
      "desc": "用這個時框確認進場時機（15-20字）"
    }},
    "tip": "一句話說明多時框配合的核心概念（25字以內）"
  }},
  "mistakes": [
    "常見錯誤1（20字以內）",
    "常見錯誤2（20字以內）",
    "常見錯誤3（20字以內）"
  ],
  "mistake_details": [
    "錯誤1的簡短解釋（25字以內）",
    "錯誤2的簡短解釋（25字以內）",
    "錯誤3的簡短解釋（25字以內）"
  ],
  "caption": "IG 貼文文案（用繁體中文，200-300字，含3-5個相關 hashtag）"
}}"""

    msg   = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw   = msg.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        cleaned = re.sub(r',\s*([}\]])', r'\1', match.group())
        try:
            return json.loads(cleaned)
        except Exception:
            return {}


# ── 主入口 ────────────────────────────────────────────────────────────────────

def generate_indicator_post(indicator_name: str = None) -> tuple:
    """
    生成指標教學輪播（6 張）+ caption
    回傳 (slides: list[Image], caption: str)
    """
    if indicator_name is None:
        indicator_name = get_today_indicator()

    print(f"[指標教學] 生成「{indicator_name}」...")
    data = _claude_generate(indicator_name)
    if not data:
        print("[指標教學] Claude 生成失敗，使用預設內容")
        data = {
            "hook": f"你真的懂 {indicator_name} 嗎？",
            "indicator_short": indicator_name.split("（")[0],
            "indicator_full": indicator_name,
            "what_is_it": {
                "headline": "幫助判斷市場趨勢的重要指標",
                "highlight": "正確使用可大幅提高勝率",
                "bullets": ["用於判斷趨勢方向", "可設定多種參數", "結合其他指標效果更佳", "新手也能快速上手"]
            },
            "chart_caption": "DOGE/USDT 4H K線 · 指標實際應用",
            "signals": {
                "buy":  ["指標出現多頭信號", "價格突破關鍵位置", "成交量同步放大"],
                "sell": ["指標出現空頭信號", "價格跌破支撐", "成交量萎縮"]
            },
            "mistakes": ["只看單一指標", "忽略整體趨勢", "沒有設定止損"],
            "mistake_details": ["需搭配其他指標確認", "大趨勢優先於短線信號", "嚴格止損才能長期生存"],
            "caption": f"#{indicator_name.split('（')[0]} #技術分析 #加密貨幣 #WycBotAI #新手教學"
        }

    print(f"  生成封面...")
    slides = [_slide_cover(data)]
    print(f"  生成定義...")
    slides.append(_slide_definition(data))
    print(f"  生成K線圖...")
    slides.append(_slide_chart(data, indicator_name))
    print(f"  生成信號判讀...")
    slides.append(_slide_signals(data))
    print(f"  生成最佳時框...")
    slides.append(_slide_timeframes(data))
    print(f"  生成常見錯誤...")
    slides.append(_slide_mistakes(data))
    print(f"  生成CTA...")
    slides.append(_slide_cta(data))

    caption = data.get("caption", f"#{indicator_name} #技術分析 #加密貨幣 #wycbotai")
    print(f"[指標教學] 完成，共 {len(slides)} 張")
    return slides, caption


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else None
    slides, caption = generate_indicator_post(name)
    out = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out, exist_ok=True)
    for i, slide in enumerate(slides):
        path = os.path.join(out, f"indicator_{i+1}.jpg")
        slide.save(path, quality=95)
        print(f"Saved: {path}")
    print(f"\nCaption:\n{caption}")
