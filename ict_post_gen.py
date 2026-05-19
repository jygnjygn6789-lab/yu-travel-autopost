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

W, H    = 1080, 1080
BG      = (245, 241, 232)   # 米白底
BLACK   = (18,  18,  18)
GREY    = (110, 110, 110)
GREEN   = (0,   180, 100)   # WycBotAI 綠
RED     = (210,  45,  45)
DARK    = (28,  28,  28)    # 深色區塊
CREAM2  = (235, 230, 218)   # 次要底色

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
    """底部品牌：@wycbotai"""
    color = (200, 200, 200) if dark_mode else GREY
    draw.text((54, H - 60), "@wycbotai", font=fr(32), fill=color)
    draw.text((W - 260, H - 60), "wycbotai.com", font=fr(32), fill=GREEN)


def _accent_bar(draw, x=54, y=None, w=120, color=GREEN, thickness=6):
    if y is not None:
        draw.line([(x, y), (x + w, y)], fill=color, width=thickness)


# ── 1. 封面 ───────────────────────────────────────────────────────────────────

def _slide_cover(topic: str, hook: str, sub: str) -> Image.Image:
    img, draw = _canvas()

    # 頂部綠色細線
    draw.line([(0, 0), (W, 0)], fill=GREEN, width=8)

    # 主標題（超大）
    lines = _wrap(draw, hook, fb(96), W - 108)
    y = 160
    for line in lines[:3]:
        draw.text((54, y), line, font=fb(96), fill=BLACK)
        y += 118

    # 副標題
    _accent_bar(draw, y=y + 20, w=100)
    sub_lines = _wrap(draw, sub, fr(52), W - 108)
    sy = y + 48
    for line in sub_lines[:2]:
        draw.text((54, sy), line, font=fr(52), fill=GREY)
        sy += 66

    # 右下角主題 tag
    tag_fnt = fb(38)
    bb = draw.textbbox((0,0), topic, font=tag_fnt)
    tw = bb[2] - bb[0]
    draw.rounded_rectangle([W - tw - 72, H - 120, W - 40, H - 64],
                            radius=8, fill=GREEN)
    draw.text((W - tw - 54, H - 113), topic, font=tag_fnt, fill=(255,255,255))

    _brand(draw)
    return img


# ── 內容頁（問題 + 答案）─────────────────────────────────────────────────────

def _slide_qa(question: str, answer_lines: list, slide_num: int,
              highlight: str = "", color=BLACK) -> Image.Image:
    img, draw = _canvas()

    # 左上角頁碼
    draw.text((54, 42), f"{slide_num:02d}", font=fb(52), fill=CREAM2)

    # 問題標題
    q_lines = _wrap(draw, question, fb(72), W - 108)
    y = 120
    for line in q_lines[:3]:
        draw.text((54, y), line, font=fb(72), fill=color)
        y += 90

    _accent_bar(draw, y=y + 8, w=80, color=color)
    y += 40

    # Highlight box（若有）
    if highlight:
        hl_lines = _wrap(draw, highlight, fb(56), W - 140)
        box_h = len(hl_lines) * 72 + 36
        draw.rounded_rectangle([54, y, W - 54, y + box_h],
                                radius=12, fill=DARK)
        hy = y + 18
        for hl in hl_lines:
            draw.text((80, hy), hl, font=fb(56), fill=(255, 255, 255))
            hy += 72
        y = y + box_h + 36

    # 答案條列
    for ans in answer_lines[:4]:
        ans_lines = _wrap(draw, ans, fr(50), W - 130)
        # bullet
        draw.ellipse([54, y + 18, 72, y + 36], fill=GREEN)
        ay = y
        for al in ans_lines[:2]:
            draw.text((90, ay), al, font=fr(50), fill=BLACK)
            ay += 62
        y = ay + 24

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
            "title": "按讚 + 追蹤 @wycbotai",
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
      "color": "black"
    }}
  ],
  "wycbotai_title": "WycBotAI 功能頁標題（25字以內）",
  "wycbotai_points": ["AI功能點1（20字以內）", "AI功能點2", "AI功能點3", "AI功能點4"],
  "caption": "IG 文案（繁中，120-180字，含3-5個hashtag）"
}}

slides 要有 3-4 張，涵蓋：基本概念、為什麼新手犯錯、正確用法。"""

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

def generate_ict_post(topic: str = "斐波那契回調（Fibonacci Retracement）") -> tuple:
    """
    生成 ICT 聰明錢風格輪播
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
    colors = [BLACK, RED, BLACK, RED]
    for i, slide in enumerate(data.get("slides", [])[:4]):
        color_name = slide.get("color", "black")
        color = RED if color_name == "red" else BLACK
        slides.append(_slide_qa(
            question=slide.get("question", ""),
            answer_lines=slide.get("answers", []),
            slide_num=i + 1,
            highlight=slide.get("highlight", ""),
            color=color,
        ))

    # WycBotAI 功能頁
    slides.append(_slide_wycbotai(
        feature_title=data.get("wycbotai_title", "AI 幫你自動找這些位置"),
        points=data.get("wycbotai_points", [
            "AI 每日掃描 Fib 關鍵回調位",
            "自動標記 0.618-0.786 黃金區間",
            "結合成交量確認進場強度",
            "止損止盈比例自動計算",
        ])
    ))

    # CTA
    slides.append(_slide_cta(topic))

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
