"""
WycBotAI 雙日輪替內容生成器
週二四六發佈，每週交替：
  - 偶數週：華爾街名人金句（單句 + 假設案例）
  - 奇數週：新手常犯的錯
"""
import os, re, json, datetime, requests
from io import BytesIO
import anthropic
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dotenv import load_dotenv

from font_paths import FONT_BOLD, FONT_REG

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


def _canvas():
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    for x in range(60, W, 108):
        for y in range(60, H, 108):
            draw.ellipse([x-1, y-1, x+1, y+1], fill=(255, 255, 255, 6))
    return img, ImageDraw.Draw(img)


def _brand(draw):
    draw.line([(0, H - 88), (W, H - 88)], fill=(*GREEN, 25), width=1)
    draw.text((54,      H - 66), "@wycbotai",    font=fr(28), fill=(*GREY,  180))
    draw.text((W - 260, H - 66), "wycbotai.com", font=fr(28), fill=(*GREEN, 160))


def _tag(draw, text, y=52, color=GREEN):
    fnt = fb(28)
    bb  = draw.textbbox((0, 0), text, font=fnt)
    tw  = bb[2] - bb[0]; th = bb[3] - bb[1]
    px, py = 18, 8
    draw.rounded_rectangle(
        [54, y, 54 + tw + px*2, y + th + py*2],
        radius=6, fill=DIM, outline=(*color, 100), width=1
    )
    draw.text((54 + px, y + py), text, font=fnt, fill=color)


def _wrap(draw, text, font, max_w):
    lines, line = [], ""
    for ch in text:
        test = line + ch
        if draw.textbbox((0,0), test, font=font)[2] > max_w:
            if line:
                lines.append(line)
            line = ch
        else:
            line = test
    if line:
        lines.append(line)
    return lines


def _fetch_person_photo(person_name: str) -> Image.Image | None:
    """從 Wikipedia REST API 抓名人照片"""
    wiki_name = person_name.strip().replace(" ", "_")
    headers = {
        "User-Agent": "WycBotAI/1.0 (https://wycbotai.com; educational-ig-content@wycbotai.com)",
        "Accept": "image/jpeg,image/png,image/*",
    }
    try:
        # 取得摘要（含縮圖 URL）
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_name}",
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        # 優先用 originalimage（更高解析度），fallback 到 thumbnail
        url = (data.get("originalimage") or data.get("thumbnail") or {}).get("source")
        if not url:
            return None
        # 縮圖限制 800px 寬
        url = re.sub(r'/\d+px-', '/800px-', url)
        img_resp = requests.get(url, headers=headers, timeout=15)
        if img_resp.status_code == 200 and "image" in img_resp.headers.get("Content-Type", ""):
            return Image.open(BytesIO(img_resp.content)).convert("RGB")
        # fallback：直接用 thumbnail URL
        thumb_url = data.get("thumbnail", {}).get("source", "")
        if thumb_url:
            img_resp2 = requests.get(thumb_url, headers=headers, timeout=15)
            if img_resp2.status_code == 200:
                return Image.open(BytesIO(img_resp2.content)).convert("RGB")
    except Exception as e:
        print(f"[Photo] 無法取得照片: {e}")
    return None


def _photo_bg_canvas(photo: Image.Image) -> tuple:
    """用名人照片製作背景（暗化 + 模糊 + 左側半透明遮罩）"""
    # 縮放填滿畫布
    ph_ratio = photo.width / photo.height
    cv_ratio = W / H
    if ph_ratio > cv_ratio:
        new_h = H
        new_w = int(H * ph_ratio)
    else:
        new_w = W
        new_h = int(W / ph_ratio)
    photo = photo.resize((new_w, new_h), Image.LANCZOS)
    # 置中裁切
    x_off = (new_w - W) // 2
    y_off = (new_h - H) // 2
    photo = photo.crop((x_off, y_off, x_off + W, y_off + H))
    # 輕微模糊
    photo = photo.filter(ImageFilter.GaussianBlur(radius=3))
    # 暗化疊加
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 180))
    bg = photo.convert("RGBA")
    bg = Image.alpha_composite(bg, overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)
    return bg, draw


# ═══════════════════════════════════════════════════════════════════════════════
# 華爾街名人金句（單句 + 假設案例）
# ═══════════════════════════════════════════════════════════════════════════════

def _slide_quote_photo(data: dict, photo: Image.Image | None) -> Image.Image:
    """金句卡（封面）：名人照片背景 + 金句 + 作者 + context"""
    if photo:
        img, draw = _photo_bg_canvas(photo)
    else:
        img, draw = _canvas()

    # 大引號
    draw.text((54, 108), "\u201c", font=fb(180), fill=(*GOLD, 30))

    # 金句文字
    quote = data.get("quote", "")
    lines = _wrap(draw, quote, fb(68), W - 108)
    y = 210
    for line in lines[:4]:
        draw.text((54, y), line, font=fb(68), fill=WHITE)
        y += 90

    # 作者
    draw.line([(54, y + 20), (320, y + 20)], fill=GOLD, width=2)
    draw.text((54, y + 44), f"— {data.get('person_title', '')}", font=fb(44), fill=GOLD)

    # context（說話背景）
    ctx = data.get("context", "")
    ctx_y = y + 112
    if ctx:
        ctx_lines = _wrap(draw, ctx, fr(40), W - 108)
        for line in ctx_lines[:3]:
            draw.text((54, ctx_y), line, font=fr(40), fill=(*GREY, 220))
            ctx_y += 56

    _brand(draw)
    return img


def _slide_case_setup(data: dict, photo=None) -> Image.Image:
    """假設情境設定"""
    img, draw = _photo_bg_canvas(photo) if photo else _canvas()
    draw.text((W-240, 20), "01", font=fb(180), fill=(*GREEN, 10))

    draw.text((54, 148), "假設今天", font=fb(86), fill=WHITE)
    draw.text((54, 248), "你遇到這種情況", font=fb(78), fill=GREEN)
    draw.line([(54, 354), (520, 354)], fill=GREEN, width=3)

    setup = data.get("case_setup", "")
    lines = _wrap(draw, setup, fr(50), W - 108)
    y = 390
    for line in lines[:6]:
        draw.text((54, y), line, font=fr(50), fill=WHITE)
        y += 72

    _brand(draw)
    return img


def _slide_case_compare(data: dict, photo=None) -> Image.Image:
    """散戶 vs 大師：對比在同一張"""
    img, draw = _photo_bg_canvas(photo) if photo else _canvas()
    # 上半：散戶
    draw.rounded_rectangle([54, 110, W-54, 560], radius=16, fill=(40, 8, 8))
    draw.rounded_rectangle([54, 110, 66, 560], radius=4, fill=RED)
    draw.text((88, 124), "散戶的選擇", font=fb(46), fill=RED)
    without_lines = _wrap(draw, data.get("case_without", ""), fr(44), W - 140)
    wy = 184
    for line in without_lines[:4]:
        draw.text((88, wy), line, font=fr(44), fill=WHITE)
        wy += 62
    result_bad = data.get("case_without_result", "虧損出場")
    draw.rounded_rectangle([88, wy+10, 88+len(result_bad)*30+40, wy+68], radius=34, fill=RED)
    draw.text((108, wy+18), f"結果：{result_bad}", font=fb(38), fill=WHITE)

    # 中間分隔
    draw.text((W//2 - 28, 572), "VS", font=fb(52), fill=GOLD)

    # 下半：大師
    draw.rounded_rectangle([54, 640, W-54, 1090], radius=16, fill=(0, 36, 18))
    draw.rounded_rectangle([54, 640, 66, 1090], radius=4, fill=GREEN)
    draw.text((88, 654), "大師的選擇", font=fb(46), fill=GREEN)
    with_lines = _wrap(draw, data.get("case_with", ""), fr(44), W - 140)
    gwy = 714
    for line in with_lines[:4]:
        draw.text((88, gwy), line, font=fr(44), fill=WHITE)
        gwy += 62
    result_good = data.get("case_with_result", "穩定獲利")
    draw.rounded_rectangle([88, gwy+10, 88+len(result_good)*30+40, gwy+68], radius=34, fill=GREEN)
    draw.text((108, gwy+18), f"結果：{result_good}", font=fb(38), fill=BG)

    _brand(draw)
    return img


def _slide_quote_cta(data: dict, photo=None) -> Image.Image:
    img, draw = _photo_bg_canvas(photo) if photo else _canvas()
    draw.text((54, 170), "把大師智慧",       font=fb(86), fill=WHITE)
    draw.text((54, 268), "變成你的獲利系統", font=fb(72), fill=WHITE)
    draw.line([(54, 380), (W - 54, 380)], fill=(*GREEN, 40), width=1)

    features = [
        "AI 自動執行大師級策略邏輯",
        "三重指標過濾，降低人性失誤",
        "即時信號推播，不錯過每個機會",
    ]
    y = 416
    for feat in features:
        draw.text((54,  y), ">>", font=fb(40), fill=GREEN)
        draw.text((124, y), feat, font=fr(40), fill=WHITE)
        y += 68

    # 留言提示（無背景框，純文字）
    cta_y = y + 40
    draw.text((54, cta_y),      "留言",         font=fr(40), fill=GREY)
    draw.text((54, cta_y + 50), "金句",          font=fb(56), fill=GOLD)
    draw.text((54, cta_y + 116),"我傳策略連結給你", font=fr(40), fill=WHITE)

    draw.text((54, H - 164), "追蹤 @wycbotai 每日策略不錯過", font=fr(36), fill=GREY)
    _brand(draw)
    return img


def _claude_single_quote() -> dict:
    client = anthropic.Anthropic()
    prompt = """你是加密貨幣交易教育專家，為 WycBotAI 策略網站的 Instagram 帳號生成內容。

生成「今日交易金句」輪播貼文，選一位真實的華爾街/交易傳奇人物，一句名言，配上假設案例講解。

要求：
- 繁體中文，口語化，針對新手散戶
- 不要提及任何幣種名稱，用「這個市場」「價格」「K線」等通用詞
- 假設情境要具體有畫面感（有數字更好，如「你有 5000 USDT」）
- 對比要強烈：散戶常見錯誤 vs 按照金句邏輯的做法
- 必須從以下名單選人（Wikipedia 有照片）：Warren Buffett、George Soros、Ray Dalio、Paul Tudor Jones、Stanley Druckenmiller、Charlie Munger、Peter Lynch、Howard Marks、Bill Ackman、Michael Burry

嚴格回傳以下 JSON，不要有任何多餘文字：

{
  "person_name": "英文姓名（用於 Wikipedia 搜尋，如 Warren Buffett）",
  "person_title": "姓名 · 中文身份（如 Warren Buffett · 股神）",
  "quote": "金句翻譯（25-40字，自然流暢）",
  "context": "這句話的背景或說話時機（20-30字）",
  "case_setup": "假設情境：你有多少資金，市場出現什麼訊號，你面臨什麼選擇（40-55字）",
  "case_without": "不照金句做：散戶的典型操作是什麼，心理狀態如何（40-55字）",
  "case_without_result": "最後結果（6-10字，如：停損出場虧損15%）",
  "case_with": "照金句做：用金句邏輯來思考，操作方式是什麼（40-55字）",
  "case_with_result": "最後結果（6-10字，如：獲利了結賺18%）",
  "caption": "IG 貼文文案（繁體中文，150-250字，含3-5個相關 hashtag）"
}"""

    msg = client.messages.create(
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
    except Exception:
        cleaned = re.sub(r',\s*([}\]])', r'\1', match.group())
        try:
            return json.loads(cleaned)
        except Exception:
            return {}


def generate_quotes_post() -> tuple:
    """生成今日金句輪播（6張）+ caption"""
    print("[WycBotAI Alt] 生成「今日交易金句」...")
    data = _claude_single_quote()

    # 抓名人照片
    person_name = data.get("person_name", "")
    photo = None
    if person_name:
        print(f"[WycBotAI Alt] 抓取 {person_name} 的照片...")
        photo = _fetch_person_photo(person_name)
        if photo:
            print(f"[WycBotAI Alt] 照片取得成功")
        else:
            print(f"[WycBotAI Alt] 照片取得失敗，使用暗色背景")

    slides = [
        _slide_quote_photo(data, photo),
        _slide_case_setup(data, photo),
        _slide_case_compare(data, photo),
        _slide_quote_cta(data, photo),
    ]
    caption = data.get("caption", "#wycbotai #交易金句 #投資智慧 #技術分析 #加密貨幣")
    print(f"[WycBotAI Alt] 完成，共 {len(slides)} 張")
    return slides, caption


# ═══════════════════════════════════════════════════════════════════════════════
# 新手常犯的錯
# ═══════════════════════════════════════════════════════════════════════════════

def _mistakes_cover(data: dict) -> Image.Image:
    img, draw = _canvas()
    _tag(draw, "WYCBOTAI · 新手必讀", color=RED)

    draw.text((54, 160), data.get("hook_num", "95%"), font=fb(200), fill=RED)
    y = 390
    for line in [data.get("hook_line1", "的新手"), data.get("hook_line2", "都踩過這些坑")]:
        if line:
            draw.text((54, y), line, font=fb(78), fill=WHITE)
            y += 90

    draw.line([(54, y + 10), (420, y + 10)], fill=RED, width=3)
    sub_lines = _wrap(draw, data.get("subtitle", ""), fr(44), W - 108)
    sy = y + 44
    for l in sub_lines[:2]:
        draw.text((54, sy), l, font=fr(44), fill=GREY)
        sy += 62

    _brand(draw)
    return img


def _mistake_card(mistake: dict, index: int) -> Image.Image:
    img, draw = _canvas()
    _tag(draw, f"WYCBOTAI · 錯誤 {index:02d}", color=RED)

    draw.text((W - 260, 20), f"{index:02d}", font=fb(180), fill=(*RED, 12))

    title = mistake.get("title", "")
    draw.rounded_rectangle([54, 148, W - 54, 268], radius=14, fill=(50, 10, 10))
    draw.rounded_rectangle([54, 148, 66, 268], radius=4, fill=RED)
    t_lines = _wrap(draw, title, fb(52), W - 140)
    ty = 162
    for l in t_lines[:2]:
        draw.text((88, ty), l, font=fb(52), fill=RED)
        ty += 64

    draw.text((54, 290), "為什麼會這樣？", font=fb(38), fill=GREY)
    draw.line([(54, 334), (340, 334)], fill=(*GREY, 80), width=1)
    prob_lines = _wrap(draw, mistake.get("problem", ""), fr(44), W - 108)
    py = 350
    for l in prob_lines[:3]:
        draw.text((54, py), l, font=fr(44), fill=WHITE)
        py += 62

    sol_y = py + 32
    draw.text((54, sol_y), "正確做法", font=fb(38), fill=GREEN)
    draw.line([(54, sol_y + 48), (280, sol_y + 48)], fill=(*GREEN, 80), width=1)
    sol_lines = _wrap(draw, mistake.get("solution", ""), fr(44), W - 108)
    ey = sol_y + 64
    for l in sol_lines[:3]:
        draw.text((54, ey), l, font=fr(44), fill=WHITE)
        ey += 62

    _brand(draw)
    return img


def _mistakes_cta(data: dict) -> Image.Image:
    img, draw = _canvas()
    _tag(draw, "WYCBOTAI · 免費體驗")

    draw.text((54, 170), "避開錯誤還不夠，", font=fb(72), fill=WHITE)
    draw.text((54, 256), "你需要 AI 主動提醒",  font=fb(68), fill=WHITE)
    draw.line([(54, 358), (W - 54, 358)], fill=(*GREEN, 40), width=1)

    features = [
        "AI 即時偵測你的錯誤操作模式",
        "每日信號幫你避開假突破陷阱",
        "自動止損計算，不再情緒下單",
    ]
    y = 394
    for feat in features:
        draw.text((54,  y), ">>", font=fb(40), fill=GREEN)
        draw.text((124, y), feat, font=fr(40), fill=WHITE)
        y += 68

    cta_y = y + 32
    box_h = 130
    draw.rounded_rectangle([54, cta_y, W - 54, cta_y + box_h], radius=16, fill=DIM)
    draw.rounded_rectangle([54, cta_y, 66, cta_y + box_h], radius=4, fill=RED)
    draw.text((88, cta_y + 14), "留言", font=fr(36), fill=GREY)
    kw_fnt = fb(60)
    kw = "避雷"
    bb = draw.textbbox((0,0), kw, font=kw_fnt)
    kw_w = bb[2]-bb[0]; kw_h = bb[3]-bb[1]
    draw.rounded_rectangle([88, cta_y+54, 88+kw_w+20, cta_y+54+kw_h+8], radius=8, fill=(50,0,0))
    draw.text((98, cta_y+56), kw, font=kw_fnt, fill=RED)
    draw.text((88+kw_w+32, cta_y+66), "我私訊給你避雷清單", font=fr(38), fill=WHITE)

    by = H - 296
    draw.rounded_rectangle([54, by, W - 54, by + 100], radius=50, fill=GREEN)
    txt = "前往 wycbotai.com 免費體驗"
    bb2 = draw.textbbox((0,0), txt, font=fb(42))
    draw.text(((W - (bb2[2]-bb2[0])) // 2, by + 24), txt, font=fb(42), fill=BG)
    draw.text((54, H - 164), "追蹤 @wycbotai 每日策略不錯過", font=fr(36), fill=GREY)
    _brand(draw)
    return img


def _claude_mistakes() -> dict:
    client = anthropic.Anthropic()
    prompt = """你是加密貨幣交易教育專家，為 WycBotAI 策略網站的 Instagram 帳號生成內容。

生成「新手常犯的錯誤」輪播貼文的內容。

要求：
- 繁體中文，口語化，針對完全新手
- 錯誤要真實常見，不要泛泛而談
- 正確做法要具體，有可執行性
- 不要提及幣種名稱

嚴格回傳以下 JSON，不要有任何多餘文字：

{
  "hook_num": "一個衝擊數字（如 95%）",
  "hook_line1": "封面第二行（6字以內）",
  "hook_line2": "封面第三行（9字以內）",
  "subtitle": "副標（20字以內）",
  "mistakes": [
    {
      "title": "錯誤標題（12字以內）",
      "problem": "為什麼這樣做會虧錢（30-40字）",
      "solution": "正確的做法（30-40字）"
    },
    { "title": "錯誤2", "problem": "...", "solution": "..." },
    { "title": "錯誤3", "problem": "...", "solution": "..." },
    { "title": "錯誤4", "problem": "...", "solution": "..." }
  ],
  "caption": "IG 貼文文案（繁體中文，150-250字，含3-5個相關 hashtag）"
}"""

    msg = client.messages.create(
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
    except Exception:
        cleaned = re.sub(r',\s*([}\]])', r'\1', match.group())
        try:
            return json.loads(cleaned)
        except Exception:
            return {}


def generate_mistakes_post() -> tuple:
    """生成新手常犯錯誤輪播（6張）+ caption"""
    print("[WycBotAI Alt] 生成「新手常犯的錯」...")
    data = _claude_mistakes()
    slides = [_mistakes_cover(data)]
    for i, m in enumerate(data.get("mistakes", [])[:4], start=1):
        slides.append(_mistake_card(m, i))
    slides.append(_mistakes_cta(data))
    caption = data.get("caption", "#wycbotai #交易新手 #投資理財 #技術分析 #加密貨幣")
    print(f"[WycBotAI Alt] 完成，共 {len(slides)} 張")
    return slides, caption


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

def get_today_alt_post() -> tuple:
    """偶數週 → 金句；奇數週 → 新手常犯的錯"""
    week = datetime.date.today().isocalendar()[1]
    if week % 2 == 0:
        return generate_quotes_post()
    else:
        return generate_mistakes_post()


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if mode == "quotes":
        slides, caption = generate_quotes_post()
        label = "quotes"
    elif mode == "mistakes":
        slides, caption = generate_mistakes_post()
        label = "mistakes"
    else:
        slides, caption = get_today_alt_post()
        label = "alt"

    out = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out, exist_ok=True)
    for i, s in enumerate(slides):
        path = os.path.join(out, f"preview_{label}_{i+1}.jpg")
        s.save(path, quality=95)
        print(f"Saved: {path}")
    print(f"\nCaption:\n{caption}")
