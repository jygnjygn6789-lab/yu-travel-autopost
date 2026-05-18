"""
極簡海報風格旅遊懶人包生成模組
對標 @japanuts / @thaihi_travel 主流 IG 手法
全版照片底 + 漸層 + 大字標題，乾淨有力
封面 + 6 張內容卡，共 7 張
"""
import os
import json
import re
import anthropic
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pilmoji import Pilmoji
from dotenv import load_dotenv

from guide_gen import fb, fr, wrap_text
from pexels import get_travel_photo, search_photos, download_image
from font_paths import FONT_KAIU

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

SIZE      = (1080, 1350)     # 4:5 直式，佔更多螢幕


def ov_rounded(img, box, radius, fill_rgba):
    """根據圖片實際尺寸建立 overlay，避免尺寸不符錯誤"""
    rgba = img.convert("RGBA")
    ov   = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(box, radius=radius, fill=fill_rgba)
    return Image.alpha_composite(rgba, ov).convert("RGB")


def ov_rect(img, box, fill_rgba):
    rgba = img.convert("RGBA")
    ov   = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle(box, fill=fill_rgba)
    return Image.alpha_composite(rgba, ov).convert("RGB")
WHITE     = (255, 255, 255)
OFF_WHITE = (238, 232, 218)
GOLD      = (245, 197, 0)
GOLD_DIM  = (200, 160, 0)
CORAL     = (210, 68, 52)    # 類別標籤底色（參考 @japanuts）
BLACK_OV  = (0, 0, 0)


# ── 工具 ──────────────────────────────────────────────────────────────────────

def _gradient(img, start_frac=0.30, top_a=55, bot_a=225):
    """全版漸層：上方輕微暗化，下方大漸層"""
    w, h = img.size
    from PIL import Image as _I, ImageDraw as _D
    rgba = img.convert("RGBA")
    ov   = _I.new("RGBA", (w, h), (0, 0, 0, 0))
    d    = _D.Draw(ov)
    sy   = int(h * start_frac)
    for y in range(sy):
        a = int(top_a * (1 - y / sy) ** 2)
        d.line([(0, y), (w-1, y)], fill=(0, 0, 0, a))
    for y in range(sy, h):
        t = (y - sy) / (h - sy)
        a = int(bot_a * (t ** 0.55))
        d.line([(0, y), (w-1, y)], fill=(0, 0, 0, a))
    return _I.alpha_composite(rgba, ov).convert("RGB")


def _tag_pill(img, text, y, color=CORAL):
    """居中彩色藥丸標籤"""
    w = img.size[0]
    fnt = fb(34)
    draw = ImageDraw.Draw(img)
    bb   = draw.textbbox((0, 0), text, font=fnt)
    tw   = bb[2] - bb[0]
    px, py = 32, 14
    pill_w = tw + px * 2
    pill_h = bb[3] - bb[1] + py * 2
    x0 = (w - pill_w) // 2
    img  = ov_rounded(img, [x0, y, x0+pill_w, y+pill_h], pill_h//2, (*color, 235))
    draw = ImageDraw.Draw(img)
    draw.text((x0+px, y+py), text, font=fnt, fill=WHITE)
    return img, y + pill_h + 18


def _big_title(img, lines, y, size=118):
    """居中大標題（標楷體）+ 陰影"""
    w    = img.size[0]
    fnt  = ImageFont.truetype(FONT_KAIU, size)
    draw = ImageDraw.Draw(img)
    lh   = size + 24
    for i, line in enumerate(lines):
        bb = draw.textbbox((0, 0), line, font=fnt)
        tx = (w - (bb[2]-bb[0])) // 2
        ty = y + i * lh
        draw.text((tx+5, ty+5), line, font=fnt, fill=(0, 0, 0, 170))
        draw.text((tx, ty), line, font=fnt, fill=WHITE)
    return img, y + len(lines) * lh


def _watermark(img):
    draw = ImageDraw.Draw(img)
    draw.text((46, 34), "@taiwan.travel.deals", font=fr(24), fill=(255, 255, 255, 70))
    return img


def _footer(img):
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.text((52, h-72), "@taiwan.travel.deals", font=fr(30), fill=(200, 188, 165, 220))
    draw.text((w-228, h-72), "主頁連結 >>", font=fr(30), fill=(*GOLD, 220))
    return img


# ── 封面 ──────────────────────────────────────────────────────────────────────

def _draw_cover(tag, title_lines, subtitle, keyword, bg_query):
    """
    封面：類別標籤 + 大標題（2行）+ 副標 + 留言 CTA
    """
    bg  = get_travel_photo(bg_query, "", SIZE)
    bg  = ImageEnhance.Brightness(bg).enhance(0.82)
    img = _gradient(bg, start_frac=0.28, top_a=60, bot_a=230)
    img = _watermark(img)
    w, h = SIZE

    # 類別標籤 (垂直居中約 y=470)
    img, y = _tag_pill(img, f"・{tag}・", y=475, color=CORAL)

    # 大標題
    img, y = _big_title(img, title_lines, y + 20, size=120)

    # 副標題
    if subtitle:
        draw = ImageDraw.Draw(img)
        fnt_sub = fb(40)
        bb  = draw.textbbox((0, 0), subtitle, font=fnt_sub)
        tx  = (w - (bb[2]-bb[0])) // 2
        draw.text((tx, y + 22), subtitle, font=fnt_sub, fill=(*GOLD, 235))
        y  += 22 + (bb[3]-bb[1]) + 10

    # 留言 CTA
    cta     = f"留言「{keyword}」取得完整攻略"
    fnt_cta = fb(36)
    draw    = ImageDraw.Draw(img)
    bb      = draw.textbbox((0, 0), cta, font=fnt_cta)
    cw      = bb[2]-bb[0]
    cx0     = (w-cw)//2 - 28
    cta_y   = h - 210
    img  = ov_rounded(img, [cx0, cta_y, cx0+cw+56, cta_y+60], 30, (0, 0, 0, 175))
    draw = ImageDraw.Draw(img)
    draw.text(((w-cw)//2, cta_y+12), cta, font=fnt_cta, fill=(*GOLD, 255))

    # 往下滑提示
    draw = ImageDraw.Draw(img)
    hint = ">> 往下滑看完整攻略"
    bb2  = draw.textbbox((0, 0), hint, font=fr(28))
    draw.text(((w-(bb2[2]-bb2[0]))//2, h-130), hint, font=fr(28), fill=(200, 188, 165, 180))

    return _footer(img)


# ── 內容卡 ────────────────────────────────────────────────────────────────────

def _draw_content_card(step_num, tag, title, details, bg_query):
    """
    @japanuts 風格內容卡：
    - 淺粉色底（非照片底）
    - 頂部：小主題標籤 + 驚嘆號 + 大黑色標題
    - 中間：相關照片（全寬）
    - 底部：珊瑚色橫帶 + 白色詳細說明
    """
    w, h = SIZE
    BG_PINK  = (255, 240, 242)   # 淺粉底
    CORAL_BG = (220, 60, 50)     # 底部橫帶珊瑚色
    DARK     = (30, 30, 30)

    # ── 底圖：淺粉色 ─────────────────────────────────────────────────────────
    img  = Image.new("RGB", SIZE, BG_PINK)
    draw = ImageDraw.Draw(img)

    # ── 頂部主題標籤（左對齊小字） ───────────────────────────────────────────
    fnt_tag = fb(34)
    draw.text((56, 56), f"・{tag}・", font=fnt_tag, fill=CORAL_BG)

    # ── 驚嘆號（大型，珊瑚色，左側） ────────────────────────────────────────
    fnt_excl = ImageFont.truetype(FONT_KAIU, 160)
    draw.text((46, 95), "!", font=fnt_excl, fill=CORAL_BG)

    # ── 大標題（標楷體，深色，驚嘆號右側）─────────────────────────────────────
    fnt_title = ImageFont.truetype(FONT_KAIU, 118)
    title_x   = 190
    title_y   = 108
    # 自動換行（最多 2 行）
    title_lines = _word_wrap(title, fnt_title, w - title_x - 40, draw)[:2]
    lh_title    = 130
    for i, line in enumerate(title_lines):
        draw.text((title_x, title_y + i * lh_title), line, font=fnt_title, fill=DARK)
    headline_bot = title_y + len(title_lines) * lh_title + 16

    # ── 珊瑚色分隔線 ─────────────────────────────────────────────────────────
    draw.line([(46, headline_bot), (w - 46, headline_bot)], fill=CORAL_BG, width=4)

    # ── 中間照片 ─────────────────────────────────────────────────────────────
    photo_top = headline_bot + 8
    band_h    = 360          # 底部橫帶高度
    photo_bot = h - band_h
    photo_h   = photo_bot - photo_top

    try:
        photo = get_travel_photo(bg_query, "", (w, photo_h))
        photo = photo.resize((w, photo_h), Image.LANCZOS)
        img.paste(photo, (0, photo_top))
    except Exception:
        # fallback: 深灰色塊
        draw.rectangle([0, photo_top, w, photo_bot], fill=(180, 180, 180))

    draw = ImageDraw.Draw(img)   # photo paste 後重建 draw

    # ── 底部珊瑚色橫帶 ───────────────────────────────────────────────────────
    draw.rectangle([0, photo_bot, w, h], fill=CORAL_BG)

    # ── 底帶白色說明文字（2 條，合併成段落，粗體） ────────────────────────────
    fnt_d   = fb(44)
    text_x  = 52
    text_y  = photo_bot + 32
    lh      = 60
    # 把 2 條 details 合在一起跑 word wrap
    combined = "　".join(details[:2])   # 全形空格分隔兩條
    lines    = _word_wrap(combined, fnt_d, w - text_x * 2, draw)
    for j, line in enumerate(lines[:5]):
        draw.text((text_x, text_y + j * lh), line, font=fnt_d, fill=WHITE)

    # ── 浮水印（左下） ───────────────────────────────────────────────────────
    draw.text((text_x, h - 46), "@taiwan.travel.deals", font=fr(26), fill=(255, 255, 255, 150))

    return img


# ── 字詞換行（不切斷英數連續段）────────────────────────────────────────────────

def _word_wrap(text: str, font, max_w: int, draw) -> list:
    """
    換行時不切斷英數字/符號連續段（例如 NT$800 不會被斷開）。
    """
    import re as _re
    # 先按「空格」或「中文字後」分 token
    tokens = _re.findall(r'[A-Za-z0-9$%/.#_+-]+|[^\x00-\x7F]|\s', text)
    lines, cur = [], ""
    for tok in tokens:
        test = cur + tok
        bb   = draw.textbbox((0, 0), test.strip(), font=font)
        if (bb[2] - bb[0]) > max_w and cur.strip():
            lines.append(cur.strip())
            cur = tok
        else:
            cur = test
    if cur.strip():
        lines.append(cur.strip())
    return lines


# ── JSON 修復工具 ─────────────────────────────────────────────────────────────

def _safe_json(s: str) -> dict:
    """Parse JSON, fixing common LLM output issues (literal newlines in strings)."""
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Fix: replace literal newlines inside JSON strings with a space
    chars, in_str, esc = [], False, False
    for ch in s:
        if esc:
            chars.append(ch); esc = False
        elif ch == '\\':
            chars.append(ch); esc = True
        elif ch == '"':
            in_str = not in_str; chars.append(ch)
        elif ch == '\n' and in_str:
            chars.append(' ')   # collapse newline inside string
        else:
            chars.append(ch)
    cleaned = ''.join(chars)
    # Also remove trailing commas before } or ]
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[JSON] 解析失敗：{e}")
        print(f"[JSON] 原始前300字：{s[:300]}")
        return {}


# ── Claude 內容生成 ───────────────────────────────────────────────────────────

def _claude_generate(topic: str, mode: str) -> dict:
    """
    mode = "destination"（目的地）or "tip"（出國知識）
    回傳結構化 JSON 供 7 張圖卡使用
    """
    client = anthropic.Anthropic()

    if mode == "destination":
        prompt = f"""你是台灣旅遊達人，請為「{topic}」生成一篇 IG 爆款旅遊懶人包。
繁體中文，台灣人視角，要非常具體（品牌名、NT$金額、交通工具名、App名、時間）。

每張卡只有 2 條 details，每條必須寫得詳細完整（30-50字），包含具體數字和行動建議，讓讀者直接照做。
不要寫短句，要寫完整的實用資訊。
details 不要包含韓文/日文/原文字，全部用繁體中文。

嚴格以下列 JSON 格式回應，cards 必須有完整 6 個物件，caption_steps 必須有完整 6 條：

{{
  "tag": "韓國旅遊",
  "title_l1": "{topic}",
  "title_l2": "完整攻略",
  "subtitle": "機票 住宿 交通 美食 全包",
  "keyword": "{topic}",
  "cards": [
    {{"title": "訂機票時機", "details": ["提前45天訂最省錢！長榮或華航直飛仁川來回約NT$6,500起，飛行只要2.5小時，建議用Google Flights開啟追蹤週二三出發票價通常更低", "廉航樂桃或酷航最低約NT$3,500，但要記得加購20kg行李約NT$800，避開韓國演唱會和連假旺季否則票價翻倍"], "bg_query": "airplane flight window seat"}},
    {{"title": "住哪最划算", "details": ["明洞購物最方便，飯店雙人房約NT$2,500-3,500/晚；弘大年輕氣氛好、民宿最低NT$1,200起；東大門24小時購物適合夜貓子", "Booking.com 提前3週訂有早鳥優惠，搜尋「弘大民宿」或「明洞商務飯店」評分8分以上C/P值最高，避開首爾馬拉松週末"], "bg_query": "hotel room cozy bed interior"}},
    {{"title": "交通攻略", "details": ["機場快線直達首爾站只要43分鐘、票價NT$480，到站後轉地鐵超方便；買T-money卡NT$200加儲值，搭地鐵每趟約NT$35比單程票便宜10%", "叫車用韓國版Uber「Kakao Taxi」免現金、費用比台灣Uber便宜20%，地鐵搭到晚上12點後改叫車，首爾地鐵共9條線涵蓋所有景點"], "bg_query": "seoul metro subway transit"}},
    {{"title": "必吃美食", "details": ["橋村炸雞弘大店必點蜂蜜醬半半炸雞約NT$550，建議下午4點前去避開排隊；廣藏市場鐘路5街的綠豆煎餅NT$120和辣炒年糕NT$80是在地人早午餐", "新村血腸湯道地解酒湯一碗NT$150，五花肉烤肉選「黑豬肉」比一般豬肉香；便利店CU或GS25的起司辣炒年糕杯和三角飯糰必買，一頓飯只要NT$80"], "bg_query": "korean food street food market"}},
    {{"title": "eSIM 推薦", "details": ["Airalo韓國7天吃到飽NT$280，速度穩定4G/5G；Klook eSIM 5天NT$299下單後立刻收到QR碼，比台灣電信漫遊方案省下70%費用完全不需要換實體SIM", "出發前在手機「設定→行動網路→新增eSIM」掃碼啟用，下飛機後自動連線；建議備份原台灣SIM卡接聽電話，eSIM專心跑網路兩全其美"], "bg_query": "smartphone esim travel korea"}},
    {{"title": "出發前注意", "details": ["K-ETA電子旅遊授權要提前3天申請，費用免費，在官網填護照資料約10分鐘完成；韓元匯率約1KRW=NT$0.023，建議在台灣換好韓元，機場匯率最差", "樂天超市和免稅店購物滿NT$1,500記得索取退稅單，回國在機場退稅約退8%；韓國插座是圓形雙孔220V，台灣電器可直接用不需變壓器"], "bg_query": "passport travel preparation document"}}
  ],
  "caption_steps": [
    "【機票】提前45天訂最便宜。長榮/華航直飛首爾約NT$6500起來回，樂桃/酷航更便宜但需加購行李20kg約NT$800。建議用Google Flights比價，週二三出發通常更低。",
    "【住宿】明洞、弘大、東大門三區最熱門。明洞購物方便但貴，弘大年輕氣氛好，Booking訂飯店提前3週有早鳥優惠，雙人房NT$2000-4000/晚。",
    "【交通】機場快線AREX從仁川機場到首爾站43分鐘NT$480，購T-money卡NT$200儲值即用，搭地鐵/公車刷卡比單程票更便宜。",
    "【美食】一蘭拉麵（明洞店）、橋村炸雞、廣藏市場必去。烤肉選五花肉或牛小腸，建議午餐時段人較少。便利店CU/GS25的飯糰和關東煮很道地。",
    "【eSIM】Airalo韓國7天NT$280起，Klook eSIM 5天NT$299，出發前在App買好掃QR碼啟用，全程4G不斷線。比漫遊省70%費用。",
    "【注意事項】需申請K-ETA電子旅遊授權（免費，提前3天申請）。匯率約0.023，多帶現金。樂天超市可退稅，購物NT$1500以上記得索取退稅單。"
  ]
}}"""

    else:  # tip
        prompt = f"""你是台灣旅遊達人，請為出國主題「{topic}」生成一篇 IG 爆款懶人包。
繁體中文，台灣人視角，要非常具體（品牌名、NT$金額、App名、步驟、時間）。

每張卡只有 2 條 details，每條必須寫得詳細完整（30-50字），包含具體數字和行動建議，讓讀者直接照做。
不要寫短句，要寫完整的實用資訊。details 不要包含外文原文字，全部用繁體中文。

嚴格以下列 JSON 格式回應，cards 必須有完整 6 個物件，caption_steps 必須有完整 6 條：

{{
  "tag": "出國必知",
  "title_l1": "旅遊醫療險",
  "title_l2": "完整攻略",
  "subtitle": "出發前一定要知道的事",
  "keyword": "醫療險",
  "cards": [
    {{"title": "為什麼要買", "details": ["在日本住院一晚費用約NT$3萬，美國急診不含手術費高達NT$30萬以上，信用卡附的旅遊險通常只有「意外身故」不含醫療，光靠信用卡根本不夠", "旅遊醫療險7天只要NT$200-600，換算每天不到NT$100，萬一在海外生病或受傷，一張保單可以直接向當地醫院請款無需自費墊付再回台申請"], "bg_query": "travel insurance document passport"}},
    {{"title": "最重要的保障", "details": ["海外急診醫療費用至少要保NT$300萬，在美國、日本、歐洲這個額度才夠用；緊急醫療後送（包含回台手術）建議另保NT$100萬，這項費用最高可達NT$50萬以上", "行李遺失賠償和班機延誤津貼雖然金額不大，但延誤超過4小時可領NT$1,000-3,000；行李全數遺失最高可賠NT$20,000，記得保留航空公司的遺失報告"], "bg_query": "hospital medical emergency overseas"}},
    {{"title": "信用卡附險夠嗎", "details": ["國泰世華CUBE卡附海外旅遊平安險NT$500萬，但這是「意外身故」不是醫療，生病住院完全不理賠；玉山哩程卡、台新航空卡類似，而且必須刷「全額機票」才會啟動，自己比價訂票不算", "唯一例外是少數白金/鑽石卡附有海外急診醫療NT$50-100萬，但額度遠不足；建議用信用卡附險當基礎保障，再花NT$200-400補買富邦或國泰的旅平險加強醫療部分"], "bg_query": "credit card travel payment"}},
    {{"title": "推薦保險方案", "details": ["富邦產險e旅平險7天NT$599，含海外急診醫療NT$300萬、緊急後送NT$100萬，可在官網10分鐘內完成線上投保，出發前24小時都可以買，信用卡刷卡即保", "Klook購票時可加購「旅遊保障」NT$150起，國泰產險旅平險每人7天NT$399含醫療NT$200萬；台灣人壽旅平險7天NT$389，三家都可線上投保，建議出發前一天再買確保起保日準確"], "bg_query": "insurance policy document protection"}},
    {{"title": "如何申請理賠", "details": ["出事當天立刻向當地醫院索取英文版診斷書和收據，這是理賠最重要的文件；緊急援助電話要出發前存好手機，富邦是0800-050-888、國泰是0800-001-897，打回台灣免費", "回台後30天內備齊護照影本、登機證、醫療收據和診斷書向保險公司提出申請；金額在NT$3,000以下可直接App上傳文件，3天內審核完畢直接匯入帳戶"], "bg_query": "insurance claim form document"}},
    {{"title": "常見不理賠情況", "details": ["出發前就已知的疾病（例如糖尿病、心臟病）如果在海外復發，大部分保單不理賠；從事滑雪、浮潛、騎摩托車等活動需要額外加保「特定運動險」，標準旅平險不含", "沒有正規醫療院所開立收據不算，街邊診所或自購藥品無法申請；非醫療必要的美容手術、健康檢查也不賠；出發前仔細閱讀保單「不保事項」欄位，有疑問打客服電話確認"], "bg_query": "warning caution travel safety"}}
  ],
  "caption_steps": [
    "【為什麼要買旅遊保險】海外急診費用極高，例如在日本住院一晚約NT$3萬，美國更高達NT$30萬以上。信用卡附的通常只有意外傷害，不含醫療，強烈建議另外加保。",
    "【最重要的險種】海外急診醫療至少保NT$300萬，緊急醫療運送（含後送回台）建議NT$100萬以上。行李遺失/班機延誤雖然不大，但讓人安心。",
    "【信用卡附險夠用嗎？】大部分信用卡只有「海外旅遊平安險」（意外身故），不含醫療。國泰CUBE卡、玉山哩程卡等雖有附險，但需全額刷機票才啟動。建議另外補強醫療險。",
    "【推薦保險方案】富邦e旅平險7天NT$599，含醫療NT$300萬；台灣人壽旅遊險可線上投保；Klook購票時有附加旅遊保障可一起買。出發前24小時內都可投保。",
    "【如何理賠】出事第一步：收好所有收據和診斷書（要英文版）。回台後30天內向保險公司提出申請，備齊護照、登機證、醫療收據。各家保險公司都有24小時緊急援助電話。",
    "【常見不理賠情況】已知病症復發、酒後事故、從事跳傘/潛水等極限運動（需加保特殊運動險）、沒有正規醫院收據。出發前仔細看保單條款，有疑問先打客服電話問清楚。"
  ]
}}

請根據「{topic}」這個主題重新生成適合的內容，格式完全相同但內容換成{topic}的具體知識。每條 detail 都要30-50字，非常詳細。"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw   = msg.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        return {}
    return _safe_json(match.group())


# ── 主入口 ────────────────────────────────────────────────────────────────────

def generate_minimal_guide(topic: str, mode: str = "tip") -> tuple:
    """
    生成極簡風格懶人包（7 張）+ caption
    mode: "destination" 或 "tip"
    """
    print(f"[極簡懶人包] Claude 生成「{topic}」（{mode}）...")
    data = _claude_generate(topic, mode)

    # 封面
    tag       = data.get("tag", "旅遊攻略")
    title_l1  = data.get("title_l1", topic[:4])
    title_l2  = data.get("title_l2", "完整攻略")
    subtitle  = data.get("subtitle", "")
    keyword   = data.get("keyword", topic[:3])
    bg_query  = f"{topic} travel scenic" if mode == "destination" else "travel guide preparation"

    print(f"  生成封面...")
    cards = [_draw_cover(tag, [title_l1, title_l2], subtitle, keyword, bg_query)]

    # 內容卡
    card_data = data.get("cards", [])
    for i, card in enumerate(card_data[:6]):
        title   = card.get("title", f"重點 {i+1}")
        details = card.get("details", ["詳細資訊整理中..."])
        bg_q    = card.get("bg_query", "travel guide")
        print(f"  生成第 {i+1} 張：{title}...")
        cards.append(_draw_content_card(i+1, tag, title, details, bg_q))

    # Caption（詳細 + 留言 CTA）
    steps = data.get("caption_steps", [])
    steps_text = "\n".join(f"{s}" for s in steps)

    linkinbio = "https://yu-travel-linkinbio-visibility-public-production.up.railway.app"

    caption = f"""✈️ {title_l1}{title_l2}｜{subtitle}

{steps_text}

——
機票比價 / 旅遊保險 / Klook & KKday 優惠
全部整合在主頁連結 >> {linkinbio}

💬 留言「{keyword}」我幫你整理完整懶人包
❤️ 覺得實用幫我按讚讓更多人看到
🔔 追蹤 @taiwan.travel.deals 不錯過出國攻略

#{keyword.replace(" ", "")}攻略 #出國必知 #旅遊懶人包 #台灣旅遊 #旅遊省錢 #出國準備"""

    return cards, caption
