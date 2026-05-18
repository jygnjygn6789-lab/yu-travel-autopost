"""
WycBotAI Dark Premium Style - Demo Generator
暗色系 AI 交易策略輪播樣本（4 張）
"""
from PIL import Image, ImageDraw, ImageFont
import os

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
BOLD = os.path.join(FONTS_DIR, "msjhbd.ttc")
REG  = os.path.join(FONTS_DIR, "msjh.ttc")

def fb(size): return ImageFont.truetype(BOLD, size)
def fr(size): return ImageFont.truetype(REG,  size)

SIZE = (1080, 1350)
W, H = SIZE

BG    = (8,  13,  30)
GREEN = (0,  255, 136)
GOLD  = (255,215, 0)
RED   = (255, 68, 68)
WHITE = (255,255, 255)
GREY  = (136,153, 170)
DIM   = (22,  33,  58)


def new_canvas():
    img  = Image.new("RGB", SIZE, BG)
    draw = ImageDraw.Draw(img)
    # subtle grid dots
    for x in range(54, W, 108):
        for y in range(54, H, 108):
            draw.ellipse([x-1, y-1, x+1, y+1], fill=(255, 255, 255, 8))
    return img, ImageDraw.Draw(img)


def brand_bar(img, draw):
    draw.line([(0, H-88), (W, H-88)], fill=(*GREEN, 30), width=1)
    draw.text((54,  H-66), "@wycbotai", font=fr(28), fill=(*GREY,  180))
    draw.text((W-260, H-66), "wycbotai.com", font=fr(28), fill=(*GREEN, 160))


def tag_pill(draw, text, y=52):
    fnt = fb(28)
    bb  = draw.textbbox((0, 0), text, font=fnt)
    tw  = bb[2] - bb[0]
    th  = bb[3] - bb[1]
    px, py = 18, 8
    draw.rounded_rectangle(
        [54, y, 54+tw+px*2, y+th+py*2],
        radius=6, fill=DIM, outline=(*GREEN, 100), width=1
    )
    draw.text((54+px, y+py), text, font=fnt, fill=GREEN)


# ── Slide 1: Cover ────────────────────────────────────────────────────────────
def slide_cover():
    img, draw = new_canvas()

    # decorative top/bottom lines
    draw.line([(54, 130), (W-54, 130)], fill=(*GREEN, 35), width=1)
    draw.line([(54, H-96), (W-54, H-96)], fill=(*GREEN, 35), width=1)

    tag_pill(draw, "WYCBOTAI · AI 策略教室")

    # big number hook
    draw.text((50, 170), "90%", font=fb(230), fill=GREEN)

    draw.text((54, 416), "的散戶", font=fb(82), fill=WHITE)
    draw.text((54, 514), "用錯了進場時機", font=fb(70), fill=WHITE)

    # accent line
    draw.line([(54, 625), (380, 625)], fill=GREEN, width=3)

    # body
    body = [
        "我們的 AI 每天掃描 100+ 信號",
        "自動找出最佳入場點位",
        "讓數據幫你做決策",
    ]
    y = 660
    for line in body:
        draw.text((54, y), line, font=fr(46), fill=GREY)
        y += 66

    # CTA
    draw.text((54, H-200), "往下滑看完整策略邏輯  v", font=fb(40), fill=(*GOLD, 220))

    brand_bar(img, draw)
    return img


# ── Slide 2: Concept card ─────────────────────────────────────────────────────
def slide_concept():
    img, draw = new_canvas()

    # large bg step number
    draw.text((W-280, 30), "01", font=fb(160), fill=(*GREEN, 15))

    tag_pill(draw, "WYCBOTAI · 策略邏輯")

    # title
    draw.text((54, 190), "AI 信號是", font=fb(88), fill=WHITE)
    draw.text((54, 292), "怎麼產生的？", font=fb(88), fill=WHITE)

    # underline
    draw.line([(54, 404), (700, 404)], fill=GREEN, width=4)

    # highlight box
    bx_y = 432
    draw.rounded_rectangle([54, bx_y, W-54, bx_y+96], radius=12, fill=DIM)
    draw.rounded_rectangle([54, bx_y, 66, bx_y+96],   radius=4,  fill=GREEN)
    draw.text((90, bx_y+26), "多指標交叉驗證，勝率高達 73.2%", font=fb(40), fill=GREEN)

    # content
    items = [
        "整合 EMA / RSI / ADX 三重過濾",
        "成交量異常偵測排除假突破",
        "4H + 1D 雙時框架確認方向",
        "自動計算停損/停利比例",
    ]
    y = 564
    for item in items:
        # bullet dot
        draw.ellipse([54, y+14, 68, y+28], fill=GREEN)
        draw.text((88, y), item, font=fr(44), fill=WHITE)
        y += 72

    brand_bar(img, draw)
    return img


# ── Slide 3: Data / Stats card ────────────────────────────────────────────────
def slide_data():
    img, draw = new_canvas()

    tag_pill(draw, "WYCBOTAI · 回測數據")

    draw.text((54, 150), "策略回測成績", font=fb(82), fill=WHITE)
    draw.text((54, 252), "2022 – 2024 實盤驗證", font=fr(40), fill=GREY)
    draw.line([(54, 316), (460, 316)], fill=GREEN, width=3)

    # Stats grid (2x2)
    stats = [
        ("勝率",    "68.4%",  GREEN),
        ("年化報酬", "+127%",  GREEN),
        ("最大回撤", "-12.3%", RED),
        ("夏普比率", "2.41",   GOLD),
    ]
    cw = (W - 54*2 - 20) // 2
    ch = 216
    sy = 352
    for i, (label, val, color) in enumerate(stats):
        col = i % 2
        row = i // 2
        x = 54 + col * (cw + 20)
        y = sy + row * (ch + 20)
        draw.rounded_rectangle([x, y, x+cw, y+ch], radius=16, fill=DIM)
        # left accent
        draw.rounded_rectangle([x, y, x+6, y+ch], radius=4, fill=color)
        draw.text((x+24, y+22),  label, font=fr(36), fill=GREY)
        draw.text((x+24, y+70),  val,   font=fb(74), fill=color)

    # note
    draw.text((54, H-190), "* 基於 2022-2024 歷史回測，不代表未來報酬", font=fr(30), fill=(*GREY, 120))

    brand_bar(img, draw)
    return img


# ── Slide 4: CTA ──────────────────────────────────────────────────────────────
def slide_cta():
    img, draw = new_canvas()

    tag_pill(draw, "WYCBOTAI · 立即體驗")

    draw.text((54, 180), "準備好讓",       font=fb(90), fill=WHITE)
    draw.text((54, 284), "AI 幫你賺錢了嗎？", font=fb(76), fill=WHITE)

    draw.line([(54, 406), (W-54, 406)], fill=(*GREEN, 40), width=1)

    # feature list
    features = [
        (">>", "即時 AI 信號推播"),
        (">>", "多幣種策略自動掃描"),
        (">>", "風險控管自動計算"),
        (">>", "一鍵查看今日建議"),
    ]
    y = 440
    for icon, text in features:
        draw.text((54,  y), icon, font=fb(44), fill=GREEN)
        draw.text((130, y), text, font=fr(44), fill=WHITE)
        y += 76

    # CTA button
    btn_y = H - 340
    draw.rounded_rectangle([54, btn_y, W-54, btn_y+106], radius=53, fill=GREEN)
    txt   = "前往 wycbotai.com 免費體驗"
    bb    = draw.textbbox((0, 0), txt, font=fb(44))
    tx    = (W - (bb[2]-bb[0])) // 2
    draw.text((tx, btn_y + 26), txt, font=fb(44), fill=BG)

    draw.text((54, H-196), "追蹤 @wycbotai 每日策略更新", font=fr(38), fill=GREY)

    brand_bar(img, draw)
    return img


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out, exist_ok=True)

    slides = [
        ("demo_wyc_1_cover.jpg",   slide_cover()),
        ("demo_wyc_2_concept.jpg", slide_concept()),
        ("demo_wyc_3_data.jpg",    slide_data()),
        ("demo_wyc_4_cta.jpg",     slide_cta()),
    ]
    for fname, img in slides:
        path = os.path.join(out, fname)
        img.save(path, quality=95)
        print(f"Saved: {path}")
    print("Done!")
