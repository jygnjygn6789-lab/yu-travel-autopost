"""
沖繩視覺旅遊故事 - 對標 @okinawago.tw 風格
公式：全版美照 + 漸層 + 白線框住文字
     小字（鉤子）→ 超大粗黑標題 → 小字（地點/補充）
全部左對齊，只用白色，讓衝擊感最大化
"""
import os, re, json, random, io, time
import anthropic
import requests as _req
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from dotenv import load_dotenv
from font_paths import FONT_KAIU, FONT_BOLD, FONT_REG

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

SIZE = (1080, 1350)
W, H = SIZE
LM   = 62   # left margin

PEXELS_KEY = os.getenv("PEXELS_API_KEY", "")
PEXELS_HDR = {"Authorization": PEXELS_KEY}

WHITE     = (255, 255, 255)
OFF_WHITE = (230, 224, 212)


# ── Photo ─────────────────────────────────────────────────────────────────────

_DDGS_LAST_CALL = 0  # 全域限速

def _ddgs_images(query: str, n=5) -> list:
    """DuckDuckGo 圖片搜尋，自動限速 3 秒一次"""
    global _DDGS_LAST_CALL
    elapsed = time.time() - _DDGS_LAST_CALL
    if elapsed < 3:
        time.sleep(3 - elapsed)
    try:
        from ddgs import DDGS
        results = list(DDGS().images(query, max_results=n))
        _DDGS_LAST_CALL = time.time()
        return [r["image"] for r in results if r.get("image")]
    except Exception as e:
        print(f"[DDGS] 搜尋失敗: {e}")
        _DDGS_LAST_CALL = time.time()
        return []


def _pexels(query: str, n=8) -> list:
    try:
        r = _req.get("https://api.pexels.com/v1/search",
                     headers=PEXELS_HDR,
                     params={"query": query, "per_page": n, "orientation": "portrait"},
                     timeout=12)
        return [p["src"]["original"] for p in r.json().get("photos", [])]
    except Exception:
        return []


def _dl(url: str):
    try:
        r = _req.get(url, timeout=22, headers={"User-Agent": "Mozilla/5.0"})
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        rw, rh = img.size
        ratio = max(W / rw, H / rh)
        nw, nh = int(rw * ratio), int(rh * ratio)
        img = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - W) // 2
        top  = (nh - H) // 2
        return img.crop((left, top, left + W, top + H))
    except Exception:
        return None


def _photo(queries: list, use_ddgs=False) -> Image.Image:
    # DDGS 優先（商品圖用）
    if use_ddgs:
        for q in queries[:2]:
            urls = _ddgs_images(q, n=6)
            random.shuffle(urls)
            for url in urls[:4]:
                img = _dl(url)
                if img:
                    return img
    # Pexels
    for q in queries:
        urls = _pexels(q, n=8)
        if urls:
            for url in random.sample(urls[:5], min(3, len(urls))):
                img = _dl(url)
                if img:
                    return img
    # Unsplash 備援
    for q in queries:
        slug = q.replace(" ", ",")
        img = _dl(f"https://source.unsplash.com/1080x1350/?{slug}&sig={random.randint(1,9999)}")
        if img:
            return img
    return Image.new("RGB", SIZE, (20, 45, 70))


# ── Gradient ──────────────────────────────────────────────────────────────────

def _gradient(img: Image.Image, start=0.40, dark=210) -> Image.Image:
    """底部電影感漸層"""
    rgba = img.convert("RGBA")
    ov   = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    d    = ImageDraw.Draw(ov)
    sy   = int(H * start)
    # 頂部超輕微（讓照片保持通透）
    for y in range(min(sy, 80)):
        a = int(20 * (1 - y / 80) ** 2)
        d.line([(0, y), (W - 1, y)], fill=(0, 0, 0, a))
    # 底部強漸層
    for y in range(sy, H):
        t = (y - sy) / (H - sy)
        a = int(dark * (t ** 0.50))
        d.line([(0, y), (W - 1, y)], fill=(0, 0, 0, a))
    return Image.alpha_composite(rgba, ov).convert("RGB")


# ── Text helpers ──────────────────────────────────────────────────────────────

def _fb(size): return ImageFont.truetype(FONT_BOLD, size)
def _fr(size): return ImageFont.truetype(FONT_REG,  size)
def _fk(size): return ImageFont.truetype(FONT_KAIU, size)


def _text_left(draw, text, font, x, y, color=WHITE, shadow=True):
    """左對齊繪製，含柔和陰影"""
    if shadow:
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 140))
    draw.text((x, y), text, font=font, fill=color)
    bb = draw.textbbox((x, y), text, font=font)
    return bb[3] - bb[1]   # line height


def _hline(draw, y, alpha=200):
    """水平白線（左右各留邊）"""
    draw.line([(LM, y), (W - LM, y)], fill=(255, 255, 255, alpha), width=2)


def _watermark(draw):
    draw.text((LM, 38), "@taiwan.travel.deals",
              font=_fr(22), fill=(255, 255, 255, 85))


def _page_num(draw, cur, total):
    text = f"{cur:02d} / {total:02d}"
    font = _fr(24)
    bb   = draw.textbbox((0, 0), text, font=font)
    x    = W - (bb[2] - bb[0]) - 44
    draw.text((x + 1, 39), text, font=font, fill=(0, 0, 0, 80))
    draw.text((x, 38), text, font=font, fill=(255, 255, 255, 155))


def _wrap_bold(text: str, font, max_w: int, draw) -> list:
    """中文換行，粗體大字專用"""
    tokens = re.findall(r'[A-Za-z0-9$%/.,#_+\-！？。，、]+|[^\x00-\x7F]|\s', text)
    lines, cur = [], ""
    for tok in tokens:
        test = cur + tok
        bb   = draw.textbbox((0, 0), test.strip(), font=font)
        if bb[2] - bb[0] > max_w and cur.strip():
            lines.append(cur.strip())
            cur = tok
        else:
            cur = test
    if cur.strip():
        lines.append(cur.strip())
    return lines


# ── Text Block（核心版型）─────────────────────────────────────────────────────
#
#  ─────────────────  (上白線)
#  小字：hook / 分類
#  超大粗體標題（1-3行）
#  小字：地點 / 補充
#  ─────────────────  (下白線)

def _text_block(draw, top_small: str, title: str, bottom_small: str,
                block_top: int, title_size=102) -> int:
    """
    繪製整個文字區塊，回傳 block_bottom（下白線 y）
    block_top: 上白線的 y 座標
    """
    GAP_SMALL = 26    # 小字與白線間距
    GAP_TITLE = 30    # 標題上方間距

    y = block_top
    _hline(draw, y)
    y += GAP_SMALL

    # 小字（鉤子）
    if top_small:
        fnt_s = _fr(30)
        _text_left(draw, top_small, fnt_s, LM, y, shadow=True)
        bb = draw.textbbox((LM, y), top_small, font=fnt_s)
        y += (bb[3] - bb[1]) + GAP_TITLE
    else:
        y += GAP_TITLE

    # 超大粗體標題
    fnt_t = _fb(title_size)
    max_w = W - LM - 40
    lines = _wrap_bold(title, fnt_t, max_w, draw)
    for line in lines[:3]:
        lh = _text_left(draw, line, fnt_t, LM, y)
        y += lh + 14
    y += 18

    # 小字（地點 / 補充）
    if bottom_small:
        fnt_s2 = _fr(32)
        _text_left(draw, bottom_small, fnt_s2, LM, y, color=OFF_WHITE, shadow=True)
        bb2 = draw.textbbox((LM, y), bottom_small, font=fnt_s2)
        y += (bb2[3] - bb2[1]) + GAP_SMALL
    else:
        y += GAP_SMALL

    _hline(draw, y)
    return y  # 下白線 y


# ── Card Builders ─────────────────────────────────────────────────────────────

def _card_cover(tag: str, title: str, subtitle: str,
                photo_queries: list) -> Image.Image:
    img  = _photo(photo_queries)
    img  = ImageEnhance.Brightness(img).enhance(0.84)
    img  = _gradient(img, start=0.36, dark=220)
    draw = ImageDraw.Draw(img)

    _watermark(draw)
    _page_num(draw, 1, 7)

    # 文字區塊垂直置中於下半段
    _text_block(draw,
                top_small=tag,
                title=title,
                bottom_small=subtitle,
                block_top=720,
                title_size=110)

    # 往下滑提示
    hint = "▼  往下滑看更多"
    fnt  = _fr(24)
    bb   = draw.textbbox((0, 0), hint, font=fnt)
    draw.text(((W - (bb[2] - bb[0])) // 2, H - 72), hint,
              font=fnt, fill=(255, 255, 255, 110))
    return img


def _card_highlight(idx: int, location: str, hook: str,
                    title: str, desc: str,
                    photo_queries: list, use_ddgs=False) -> Image.Image:
    img  = _photo(photo_queries, use_ddgs=use_ddgs)
    img  = ImageEnhance.Brightness(img).enhance(0.82)
    img  = _gradient(img, start=0.43, dark=210)
    draw = ImageDraw.Draw(img)

    _watermark(draw)
    _page_num(draw, idx, 7)

    top_small    = hook if hook else location
    bottom_small = f"{location}  ·  {desc}" if (location and desc) else (location or desc)

    _text_block(draw,
                top_small=top_small,
                title=title,
                bottom_small=bottom_small,
                block_top=730,
                title_size=100)
    return img


def _card_cta(photo_queries: list) -> Image.Image:
    img  = _photo(photo_queries)
    img  = ImageEnhance.Brightness(img).enhance(0.76)
    img  = _gradient(img, start=0.30, dark=230)
    draw = ImageDraw.Draw(img)

    _watermark(draw)
    _page_num(draw, 7, 7)

    _text_block(draw,
                top_small="收藏這篇，出發前再看一次",
                title="出發前\n必看這篇",
                bottom_small="機票比價 · Klook · eSIM · 主頁連結全包",
                block_top=680,
                title_size=106)

    # 追蹤號召（白線下方）
    fnt = _fb(36)
    draw.text((LM, H - 88), "♥  追蹤 @taiwan.travel.deals",
              font=fnt, fill=(255, 255, 255, 200))
    return img


# ── Claude 生成內容 ────────────────────────────────────────────────────────────

def _claude_generate(topic: str) -> dict:
    client = anthropic.Anthropic()
    prompt = f"""你是台灣頂尖旅遊 IG 內容策劃，專門做沖繩主題帳號。
現在要做「{topic}」主題輪播，格式是「商品排行榜」，每張介紹一個具體商品。

結構：1 封面 + 5 張商品卡 + 1 CTA（共 7 張）

封面：
- tag：店名，例如「LAWSON・沖繩限定」
- title：2行以內大標，如「沖繩便利商店\n必買 TOP5」
- subtitle：一句說明，如「這幾樣台灣買不到，見到就掃」
- photo_queries：便利商店外觀或商品陳列的英文搜尋詞

5 張商品卡（每張一個商品）：
- rank：名次，格式「NO.1」到「NO.5」
- store：販售的店名，如「LAWSON」「7-ELEVEN」「FamilyMart」
- product_jp：商品日文名稱（正式商品名）
- product_zh：商品中文說明（10字內）
- price：日幣價格，如「¥198」
- hook：為什麼必買（15字內，具體衝擊感）
- title：商品名稱大標，最多 2 行，每行最多 6 字，換行用 \\n（要讓人一眼就知道是什麼）
- desc：必買理由+Tips（25字內，包含價格）
- photo_queries：這個「具體商品」的英文搜尋詞，要找到商品實物照
  - 第一個：商品日文名 + japan convenience store
  - 第二個：食材/口味關鍵字，如 purple sweet potato japan snack
  - 第三個：更廣泛的備用詞

只回傳 JSON：
{{
  "cover": {{
    "tag": "LAWSON・7-11・全家",
    "title": "沖繩便利商店\n必買 TOP5",
    "subtitle": "這幾樣台灣買不到，見到就掃",
    "photo_queries": ["japan convenience store shelves colorful", "lawson japan store interior", "japanese convenience store products display"]
  }},
  "cards": [
    {{
      "rank": "NO.1",
      "store": "LAWSON",
      "product_jp": "紅芋タルト",
      "product_zh": "紅芋塔",
      "price": "¥198",
      "hook": "沖繩最強伴手禮，比機場便宜",
      "title": "紅芋塔\n沖繩限定",
      "desc": "NO.1 LAWSON・¥198・比機場便宜 ¥80",
      "photo_queries": ["beni imo tart purple sweet potato okinawa snack", "purple sweet potato japanese sweets", "okinawa souvenir purple dessert"]
    }}
  ],
  "caption": "完整 IG 文案，emoji 豐富，條列每個商品名稱+價格+哪間店，結尾 8-10 個中文 hashtag，含 #沖繩便利商店 #沖繩必買"
}}

根據「{topic}」生成 5 個真實沖繩便利商店限定商品（LAWSON、7-ELEVEN、FamilyMart 輪流出現），
所有商品名稱、價格要真實精準，讓台灣讀者一看就想截圖存起來。"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text
    m   = re.search(r'\{.*\}', raw, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group())
    except Exception:
        try:
            return json.loads(re.sub(r',\s*([}\]])', r'\1', m.group()))
        except Exception:
            return {}


# ── 便利商店 TOP5 （硬編碼真實商品）────────────────────────────────────────────

CVS_PRODUCTS = [
    {
        "rank": "NO.1",
        "store": "LAWSON / 7-11",
        "product_jp": "オリオンドラフトビール",
        "price": "¥238",
        "title": "Orion\n生啤酒罐",
        "hook": "沖繩在地釀造，台灣買不到正版",
        "desc": "清爽麥香，沖繩海灘必配，350ml",
        "photo_queries": [
            "orion beer can 350ml okinawa japan cold",
            "orion draft beer okinawa canned beer",
            "cold beer can japan summer okinawa",
        ],
    },
    {
        "rank": "NO.2",
        "store": "全家 / LAWSON",
        "product_jp": "シークヮーサーサイダー",
        "price": "¥160前後",
        "title": "扁實檸檬\n氣泡飲",
        "hook": "沖繩限定柑橘，酸甜超解渴",
        "desc": "シークヮーサー是沖繩原生柑橘，本島買不到",
        "photo_queries": [
            "shikuwasa citrus okinawa soda drink bottle japan",
            "okinawa shikuwasa juice green citrus",
            "japanese citrus drink soda bottle",
        ],
    },
    {
        "rank": "NO.3",
        "store": "LAWSON / 7-11",
        "product_jp": "ブルーシールアイス",
        "price": "¥200起",
        "title": "Blue Seal\n霜淇淋",
        "hook": "沖繩人氣第一冰淇淋品牌",
        "desc": "紅芋・鹽味・ウベ等沖繩限定口味",
        "photo_queries": [
            "blue seal ice cream okinawa soft serve",
            "okinawa blue seal ice cream colorful flavors",
            "japanese ice cream soft serve colorful",
        ],
    },
    {
        "rank": "NO.4",
        "store": "LAWSON / 全家",
        "product_jp": "ポーク玉子おにぎり",
        "price": "¥220～257",
        "title": "豬肉玉子\n飯糰",
        "hook": "沖繩最標誌性便利商店商品",
        "desc": "SPAM豬肉+厚蛋，沖繩才有的特大飯糰",
        "photo_queries": [
            "pork tamago onigiri okinawa spam egg rice ball",
            "okinawa spam rice ball japanese onigiri",
            "japanese rice ball spam pork egg convenience",
        ],
    },
    {
        "rank": "NO.5",
        "store": "全家 / 7-11",
        "product_jp": "沖縄そばカップ麺",
        "price": "¥250前後",
        "title": "沖繩蕎麥\n限定杯麵",
        "hook": "帶回家最划算的沖繩味道",
        "desc": "豬骨+柴魚湯底，沖繩限定版包裝",
        "photo_queries": [
            "okinawa soba cup noodle japan instant ramen",
            "japanese cup noodle okinawa instant food",
            "okinawa soba noodle soup bowl food",
        ],
    },
]


def _stroke_text(draw, text, font, x, y, fill=WHITE, stroke_color=(0,0,0), stroke=6):
    """帶描邊的文字，讓白字在任何背景都清晰"""
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
    draw.text((x, y), text, font=font, fill=fill)


def _card_product(idx: int, rank: str, store: str, title: str,
                  price: str, desc: str, hook: str,
                  photo_queries: list) -> Image.Image:
    """
    @fta8716 風格：全版商品大圖 + 超大粗字描邊疊上去
    - 全版照片，底部漸層
    - 中央偏下：超大 rank 數字 + 商品名稱（描邊白字）
    - 小字：店名 + 價格
    """
    img  = _photo(photo_queries, use_ddgs=True)
    img  = ImageEnhance.Brightness(img).enhance(0.80)
    # 底部漸層（讓文字區更易讀）
    rgba = img.convert("RGBA")
    ov   = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    d_ov = ImageDraw.Draw(ov)
    for y in range(int(H * 0.45), H):
        t = (y - int(H * 0.45)) / (H * 0.55)
        a = int(180 * (t ** 0.6))
        d_ov.line([(0, y), (W - 1, y)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(rgba, ov).convert("RGB")
    draw = ImageDraw.Draw(img)

    _watermark(draw)
    _page_num(draw, idx, 7)

    # ── 超大 rank 數字（左側，半透明）──────────────────────────────
    f_rank_big = _fb(220)
    rank_num   = rank.replace("NO.", "")   # "1", "2" ...
    bb_rb = draw.textbbox((0, 0), rank_num, font=f_rank_big)
    rw = bb_rb[2] - bb_rb[0]
    rx = (W - rw) // 2
    ry = int(H * 0.36)
    # 半透明大數字底層
    num_layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    d_num = ImageDraw.Draw(num_layer)
    d_num.text((rx, ry), rank_num, font=f_rank_big, fill=(255, 255, 255, 35))
    img = Image.alpha_composite(img.convert("RGBA"), num_layer).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── 主要文字區（垂直置中於下半段）─────────────────────────────
    # 店名 + rank（小字）
    py = int(H * 0.56)
    f_label = _fr(30)
    label = f"{rank}  ·  {store}"
    bb_l  = draw.textbbox((0, 0), label, font=f_label)
    lx    = (W - (bb_l[2] - bb_l[0])) // 2
    _stroke_text(draw, label, f_label, lx, py, fill=(220, 220, 220), stroke=3)
    py += (bb_l[3] - bb_l[1]) + 22

    # 商品大標題（置中）
    f_title = _fb(130)
    max_w   = W - 80
    lines   = _wrap_bold(title, f_title, max_w, draw)
    for line in lines[:2]:
        bb_t = draw.textbbox((0, 0), line, font=f_title)
        tx = (W - (bb_t[2] - bb_t[0])) // 2
        _stroke_text(draw, line, f_title, tx, py, fill=WHITE, stroke=7)
        py += (bb_t[3] - bb_t[1]) + 8
    py += 28

    # 價格 + 一句話
    f_desc    = _fr(32)
    price_txt = f"{price}  |  {desc}" if desc else price
    bb_d  = draw.textbbox((0, 0), price_txt, font=f_desc)
    dx    = (W - (bb_d[2] - bb_d[0])) // 2
    _stroke_text(draw, price_txt, f_desc, dx, py, fill=(230, 230, 230), stroke=3)

    return img


DRUG_PRODUCTS = [
    {
        "rank": "NO.1",
        "store": "松本清 / 唐吉軻德",
        "product_jp": "ロート V5 目薬",
        "price": "¥1,500前後",
        "title": "Rohto V5\n眼藥水",
        "hook": "台灣買不到，日本必掃第一名",
        "desc": "維他命5種配方，乾眼症救星",
        "photo_queries": [
            "rohto v5 eye drops japan blue bottle",
            "rohto eyedrops japan pharmacy product",
            "japanese eye drops bottle blue rohto",
        ],
    },
    {
        "rank": "NO.2",
        "store": "松本清 / 藥妝店",
        "product_jp": "アネッサ パーフェクトUV",
        "price": "¥2,000前後",
        "title": "資生堂 Anessa\n頂級防曬",
        "hook": "SPF50+ PA++++，台灣貴一倍",
        "desc": "防水防汗，沖繩海灘必備神器",
        "photo_queries": [
            "shiseido anessa perfect UV sunscreen gold bottle japan",
            "anessa sunscreen japan SPF50 gold",
            "japanese sunscreen bottle gold shiseido",
        ],
    },
    {
        "rank": "NO.3",
        "store": "全台藥妝店",
        "product_jp": "めぐりズム 蒸気ホットアイマスク",
        "price": "¥700前後",
        "title": "花王蒸氣\n熱敷眼罩",
        "hook": "一戴就秒睡，台灣買貴30%",
        "desc": "12片入，玫瑰/無香料/薰衣草可選",
        "photo_queries": [
            "kao megurism steam eye mask japan package",
            "megurism hot eye mask japan pink box",
            "japanese steam eye mask sleep aid kao",
        ],
    },
    {
        "rank": "NO.4",
        "store": "唐吉軻德 / 松本清",
        "product_jp": "ウコンの力",
        "price": "¥200前後",
        "title": "薑黃護肝\n飲料",
        "hook": "喝酒前必備，沖繩限定版",
        "desc": "沖縄産薑黃，喝完隔天不難受",
        "photo_queries": [
            "ukon no chikara turmeric drink japan okinawa",
            "japanese turmeric liver health drink bottle",
            "okinawa ukon supplement drink yellow",
        ],
    },
    {
        "rank": "NO.5",
        "store": "全台藥妝店",
        "product_jp": "龍角散のど飴",
        "price": "¥300前後",
        "title": "龍角散\n喉糖",
        "hook": "日本藥妝必買，台灣買不到",
        "desc": "喉嚨不舒服秒救，多種口味",
        "photo_queries": [
            "ryukakusan nodo ame throat candy japan bag",
            "ryukakusan throat drops japanese pharmacy",
            "japanese throat candy lozenge ryukakusan package",
        ],
    },
]


FOOD_PRODUCTS = [
    {
        "rank": "NO.1",
        "store": "A1ステーキ",
        "product_jp": "沖繩牛排",
        "price": "¥800起",
        "title": "沖繩牛排\n超便宜",
        "hook": "台灣同等級要3倍價，必吃",
        "desc": "A1 Steak House，那霸市區，超厚牛排¥800起",
        "photo_queries": [
            "okinawa steak cheap restaurant sizzling beef plate",
            "japan steak restaurant grilled beef sizzling",
            "okinawa beef steak restaurant food",
        ],
    },
    {
        "rank": "NO.2",
        "store": "全島餐廳",
        "product_jp": "タコライス",
        "price": "¥500~800",
        "title": "塔可飯\n沖繩特有",
        "hook": "美軍帶來的沖繩限定料理",
        "desc": "墨西哥塔可料+白飯，只有沖繩才有",
        "photo_queries": [
            "taco rice okinawa japanese food colorful cheese lettuce",
            "okinawa taco rice plate restaurant food",
            "japanese taco rice american okinawa dish",
        ],
    },
    {
        "rank": "NO.3",
        "store": "在地麵店",
        "product_jp": "ソーキそば",
        "price": "¥700~1,000",
        "title": "豬軟骨\n沖繩蕎麥麵",
        "hook": "沖繩最代表性料理，必吃",
        "desc": "豬軟骨超入味，湯頭清甜，道地沖繩味",
        "photo_queries": [
            "okinawa soba noodle soup pork ribs bowl soki",
            "soki soba okinawa pork belly noodle soup",
            "okinawa noodle soup traditional bowl restaurant",
        ],
    },
    {
        "rank": "NO.4",
        "store": "海鮮餐廳 / 市場",
        "product_jp": "海ぶどう",
        "price": "¥500~800",
        "title": "海葡萄\n沖繩限定",
        "hook": "Q彈爆漿，台灣完全買不到",
        "desc": "沖繩特有海藻，配醬油和醋，口感超特別",
        "photo_queries": [
            "sea grapes umi budo okinawa green caviar plate",
            "okinawa sea grapes umibudo seaweed japanese food",
            "green sea grapes okinawa food delicacy",
        ],
    },
    {
        "rank": "NO.5",
        "store": "公設市場 / 甜點店",
        "product_jp": "サーターアンダギー",
        "price": "¥100~200",
        "title": "沖繩炸\n甜甜圈",
        "hook": "沖繩最古老街頭甜點，排隊必買",
        "desc": "外脆內鬆，黑糖紅芋口味，現炸最香",
        "photo_queries": [
            "sata andagi okinawa donut fried sweet brown traditional",
            "okinawa fried donut sweet brown ball street food",
            "japanese okinawa traditional sweet fried dough",
        ],
    },
]


def generate_food_carousel() -> tuple:
    """沖繩必吃美食 TOP5"""
    client = anthropic.Anthropic()

    caption_prompt = """請為以下沖繩必吃美食 TOP5 寫一段 IG 文案：
1. 沖繩牛排 A1 Steak House（¥800起）台灣同等級要3倍價
2. タコライス 塔可飯（¥500~800）美軍帶來的沖繩特有料理
3. ソーキそば 豬軟骨沖繩蕎麥麵（¥700~1,000）沖繩最代表料理
4. 海ぶどう 海葡萄（¥500~800）Q彈爆漿，台灣完全買不到
5. サーターアンダギー 沖繩炸甜甜圈（¥100~200）現炸最香

格式：emoji 豐富，條列每道菜+必吃理由，結尾 8 個 hashtag（含 #沖繩美食 #沖繩必吃 #沖繩旅遊）
只回傳文案，不加其他說明。"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": caption_prompt}]
    )
    caption = msg.content[0].text.strip()

    print("  [1/7] 封面...")
    cards = [_card_cover(
        tag="OKINAWA・沖繩美食",
        title="沖繩必吃\n美食 TOP5",
        subtitle="去沖繩沒吃這幾樣，等於白去",
        photo_queries=[
            "okinawa food spread traditional japanese cuisine",
            "okinawa restaurant japanese food colorful",
            "okinawa local food market street",
        ],
    )]

    for i, p in enumerate(FOOD_PRODUCTS):
        print(f"  [{i+2}/7] {p['rank']} {p['title'].replace(chr(10), ' ')}...")
        cards.append(_card_product(
            idx=i + 2,
            rank=p["rank"],
            store=p["store"],
            title=p["title"],
            price=p["price"],
            desc=p["desc"],
            hook=p["hook"],
            photo_queries=p["photo_queries"],
        ))

    print("  [7/7] CTA...")
    cards.append(_card_cta([
        "okinawa golden hour sunset sea rock",
        "okinawa sunset beach dramatic sky",
        "japan island sunset tropical",
    ]))

    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"
    if linkinbio not in caption:
        caption += f"\n\n👇 主頁連結\n{linkinbio}"

    print(f"[美食 TOP5] 完成！共 {len(cards)} 張")
    return cards, caption


def generate_drugstore_carousel() -> tuple:
    """沖繩藥妝店必買 TOP5 — 商品資料硬編碼"""
    client = anthropic.Anthropic()

    caption_prompt = """請為以下沖繩藥妝店必買 TOP5 寫一段 IG 文案：
1. ロート V5 目薬（¥1,500）台灣買不到，維他命眼藥水
2. アネッサ パーフェクトUV（¥2,000）SPF50+頂級防曬，台灣貴一倍
3. めぐりズム 蒸気ホットアイマスク（¥700）花王蒸氣眼罩，一戴就秒睡
4. ウコンの力（¥200）沖繩薑黃護肝飲，喝酒前必備
5. 龍角散のど飴（¥300）喉糖，台灣買不到

格式：emoji 豐富，條列每個商品+理由，結尾 8 個 hashtag（含 #沖繩藥妝 #日本藥妝必買 #沖繩旅遊）
只回傳文案，不加其他說明。"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": caption_prompt}]
    )
    caption = msg.content[0].text.strip()

    print("  [1/7] 封面...")
    cards = [_card_cover(
        tag="松本清・唐吉軻德・藥妝店",
        title="沖繩藥妝店\n必買 TOP5",
        subtitle="這幾樣台灣貴一倍，見到就掃",
        photo_queries=[
            "matsumoto kiyoshi japan drugstore exterior",
            "japan pharmacy drugstore shelves products",
            "japanese drugstore don quijote interior",
        ],
    )]

    for i, p in enumerate(DRUG_PRODUCTS):
        print(f"  [{i+2}/7] {p['rank']} {p['title'].replace(chr(10), ' ')}...")
        cards.append(_card_product(
            idx=i + 2,
            rank=p["rank"],
            store=p["store"],
            title=p["title"],
            price=p["price"],
            desc=p["desc"],
            hook=p["hook"],
            photo_queries=p["photo_queries"],
        ))

    print("  [7/7] CTA...")
    cards.append(_card_cta([
        "okinawa golden hour sunset sea rock",
        "okinawa sunset beach dramatic orange sky",
        "japan island sunset tropical",
    ]))

    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"
    if linkinbio not in caption:
        caption += f"\n\n👇 主頁連結\n{linkinbio}"

    print(f"[藥妝店 TOP5] 完成！共 {len(cards)} 張")
    return cards, caption


def generate_cvs_carousel() -> tuple:
    """沖繩便利商店必買 TOP5 — 商品資料硬編碼，確保正確"""
    client = anthropic.Anthropic()

    # 只讓 Claude 生成 IG 文案
    caption_prompt = """請為以下沖繩便利商店必買 TOP5 寫一段 IG 文案：
1. オリオンビール缶（LAWSON/7-11 ¥238）沖繩在地生啤
2. シークヮーサーサイダー（全家/LAWSON ¥160）沖繩限定柑橘氣泡飲
3. ブルーシールアイス（LAWSON/7-11 ¥200起）沖繩人氣第一冰淇淋
4. ポーク玉子おにぎり（LAWSON/全家 ¥220-257）沖繩招牌大飯糰
5. 沖縄そばカップ麺（全家/7-11 ¥250前後）帶回家的沖繩味道

格式：emoji 豐富，條列每個商品+理由，結尾 8 個 hashtag（含 #沖繩便利商店 #沖繩必買 #沖繩旅遊）
只回傳文案，不加其他說明。"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": caption_prompt}]
    )
    caption = msg.content[0].text.strip()

    print("  [1/7] 封面...")
    cards = [_card_cover(
        tag="LAWSON・全家・7-11",
        title="沖繩便利商店\n必買 TOP5",
        subtitle="這幾樣台灣買不到，見到就掃",
        photo_queries=[
            "lawson japan okinawa convenience store exterior",
            "japan convenience store colorful shelves",
            "okinawa konbini store japan",
        ],
    )]

    for i, p in enumerate(CVS_PRODUCTS):
        print(f"  [{i+2}/7] {p['rank']} {p['title'].replace(chr(10), ' ')}...")
        cards.append(_card_product(
            idx=i + 2,
            rank=p["rank"],
            store=p["store"],
            title=p["title"],
            price=p["price"],
            desc=p["desc"],
            hook=p["hook"],
            photo_queries=p["photo_queries"],
        ))

    print("  [7/7] CTA...")
    cards.append(_card_cta([
        "okinawa golden hour sunset sea rock",
        "okinawa sunset beach dramatic orange sky",
        "japan island sunset tropical",
    ]))

    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"
    if linkinbio not in caption:
        caption += f"\n\n👇 主頁連結\n{linkinbio}"

    print(f"[便利商店 TOP5] 完成！共 {len(cards)} 張")
    return cards, caption


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_okinawa_carousel(topic: str = "沖繩") -> tuple:
    """回傳 (cards: list[Image.Image], caption: str)"""
    print(f"[沖繩風格] Claude 生成「{topic}」內容...")
    data = _claude_generate(topic)
    if not data:
        raise RuntimeError("Claude 內容生成失敗")

    cover      = data.get("cover", {})
    highlights = data.get("cards", [])

    print("  [1/7] 封面...")
    cards = [_card_cover(
        tag=cover.get("tag", "OKINAWA・沖繩"),
        title=cover.get("title", "沖繩\n完整攻略"),
        subtitle=cover.get("subtitle", ""),
        photo_queries=cover.get("photo_queries", ["okinawa beach japan aerial"]),
    )]

    for i, h in enumerate(highlights[:5]):
        rank  = h.get("rank", f"NO.{i+1}")
        store = h.get("store", "")
        top_small = f"{rank}  {store}" if store else rank
        print(f"  [{i+2}/7] {rank} {h.get('title', '').replace(chr(10), ' ')}...")
        cards.append(_card_highlight(
            idx=i + 2,
            location=top_small,
            hook=h.get("hook", ""),
            title=h.get("title", ""),
            desc=h.get("desc", ""),
            photo_queries=h.get("photo_queries", ["japan convenience store product"]),
            use_ddgs=True,
        ))

    print("  [7/7] CTA...")
    cards.append(_card_cta([
        "okinawa golden hour sunset sea rock",
        "okinawa sunset beach dramatic orange sky",
        "japan island sunset tropical",
    ]))

    caption = data.get("caption", "#沖繩旅遊 #沖繩攻略 #台灣出發沖繩")
    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"
    if linkinbio not in caption:
        caption += f"\n\n👇 主頁連結\n{linkinbio}"

    print(f"[沖繩風格] 完成！共 {len(cards)} 張")
    return cards, caption


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out_dir = os.path.join(os.path.dirname(__file__), "output", "okinawa_v2")
    os.makedirs(out_dir, exist_ok=True)
    cards, caption = generate_okinawa_carousel("沖繩")
    for i, card in enumerate(cards):
        path = os.path.join(out_dir, f"card_{i+1:02d}.jpg")
        card.save(path, quality=92)
        print(f"  {path}")
    print(f"\n文案:\n{caption[:400]}")
