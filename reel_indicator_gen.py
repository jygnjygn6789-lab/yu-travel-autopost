"""
WycBotAI 技術指標教學 Reel 生成器
風格：暗色背景 + K線圖 + 字幕逐句同步配音
每支約 40-50 秒，1080x1920 直式
"""
import os, re, json, asyncio, tempfile, datetime
import anthropic
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from font_paths import FONT_BOLD, FONT_REG
from chart_gen import get_chart, get_chart_frames

W, H = 1080, 1920
BG    = (8,  13,  30)
GREEN = (0,  255, 136)
GOLD  = (255, 215,   0)
RED   = (255,  68,  68)
WHITE = (255, 255, 255)
GREY  = (136, 153, 170)
DIM   = (22,  33,  58)

def fb(s): return ImageFont.truetype(FONT_BOLD, s)
def fr(s): return ImageFont.truetype(FONT_REG,  s)


# ── 字幕換行 ──────────────────────────────────────────────────────────────────

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


# ── 場景畫面生成 ───────────────────────────────────────────────────────────────

def _base_canvas():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    for x in range(60, W, 108):
        for y in range(60, H, 108):
            draw.ellipse([x-1,y-1,x+1,y+1], fill=(255,255,255,6))
    return img, draw


def _draw_subtitle(draw, text, y_start=1580):
    """底部字幕區：大字白色，背景半透明"""
    fnt = fb(68)
    lines = _wrap(draw, text, fnt, W - 80)
    # 背景遮罩
    total_h = len(lines) * 88 + 32
    draw.rectangle([0, y_start - 16, W, y_start + total_h], fill=(0,0,0,160))
    y = y_start
    for line in lines[:3]:
        bb = draw.textbbox((0,0), line, font=fnt)
        x = (W - (bb[2]-bb[0])) // 2
        # 文字陰影
        draw.text((x+2, y+2), line, font=fnt, fill=(0,0,0,200))
        draw.text((x, y), line, font=fnt, fill=WHITE)
        y += 88


def _scene_intro(data: dict, subtitle: str = None) -> Image.Image:
    """封面場景：大指標名 + hook"""
    img, draw = _base_canvas()

    # 頂部細線
    draw.line([(0, 8), (W, 8)], fill=GREEN, width=4)

    # 大指標縮寫
    short = data["indicator_short"]
    fnt_big = fb(220)
    bb = draw.textbbox((0,0), short, font=fnt_big)
    x = (W - (bb[2]-bb[0])) // 2
    draw.text((x+4, 204), short, font=fnt_big, fill=(*GREEN, 30))  # 暗影
    draw.text((x, 200), short, font=fnt_big, fill=GREEN)

    # 全名
    full = data.get("indicator_full", "")
    bb2 = draw.textbbox((0,0), full, font=fr(52))
    draw.text(((W-(bb2[2]-bb2[0]))//2, 480), full, font=fr(52), fill=GREY)

    draw.line([(120, 560), (W-120, 560)], fill=(*GREEN, 60), width=1)

    # Hook 問句
    hook = data.get("hook", "你真的懂這個指標嗎？")
    hook_lines = _wrap(draw, hook, fb(84), W - 120)
    hy = 610
    for line in hook_lines[:2]:
        bb = draw.textbbox((0,0), line, font=fb(84))
        draw.text(((W-(bb[2]-bb[0]))//2, hy), line, font=fb(84), fill=WHITE)
        hy += 108

    # 三個特色 feature 卡
    features = [
        ("📈", "判斷趨勢方向"),
        ("🎯", "找進出場時機"),
        ("🛡", "控制風險止損"),
    ]
    fy = hy + 60
    card_w = (W - 108 - 2 * 20) // 3
    for j, (icon, label) in enumerate(features):
        fx = 54 + j * (card_w + 20)
        draw.rounded_rectangle([fx, fy, fx + card_w, fy + 160], radius=16, fill=DIM)
        # icon
        bi = draw.textbbox((0,0), icon, font=fb(52))
        draw.text((fx + (card_w-(bi[2]-bi[0]))//2, fy + 20), icon, font=fb(52), fill=GREEN)
        # label
        lbl_lines = _wrap(draw, label, fr(34), card_w - 16)
        ly = fy + 90
        for ll in lbl_lines[:2]:
            bl = draw.textbbox((0,0), ll, font=fr(34))
            draw.text((fx + (card_w-(bl[2]-bl[0]))//2, ly), ll, font=fr(34), fill=WHITE)
            ly += 44

    # 底部品牌
    draw.line([(0, H-80), (W, H-80)], fill=(*GREEN, 40), width=1)
    draw.text((54, H-60), "@wycbotai", font=fr(36), fill=(*GREY, 180))
    draw.text((W-300, H-60), "wycbotai.com", font=fr(36), fill=(*GREEN, 160))

    sub = subtitle if subtitle is not None else data.get("scenes", [{}])[0].get("subtitle", "")
    if sub:
        _draw_subtitle(draw, sub)
    return img


def _scene_chart(data: dict, indicator_name: str, subtitle: str) -> Image.Image:
    """K線圖場景"""
    img, draw = _base_canvas()

    # 頂部標題
    draw.line([(0, 8), (W, 8)], fill=GREEN, width=4)
    draw.text((54, 28), data["indicator_short"], font=fb(72), fill=GREEN)
    caption = data.get("chart_caption", "實際K線圖解")
    draw.text((54, 116), caption, font=fr(44), fill=GREY)
    draw.line([(54, 174), (W-54, 174)], fill=(*GREEN, 40), width=1)

    # K線圖
    chart_h = 960
    chart = get_chart(indicator_name, width=W-8, height=chart_h)
    img.paste(chart, (4, 190))

    # 底部品牌
    draw.line([(0, H-80), (W, H-80)], fill=(*GREEN, 40), width=1)
    draw.text((54, H-60), "@wycbotai", font=fr(36), fill=(*GREY, 180))

    _draw_subtitle(draw, subtitle)
    return img


def _scene_text(data: dict, scene: dict, color=GREEN, subtitle: str = None) -> Image.Image:
    """文字說明場景：大標題 + 重點條列"""
    img, draw = _base_canvas()

    draw.line([(0, 8), (W, 8)], fill=color, width=4)

    # 場景標題
    title = scene.get("title", "")
    title_fnt = fb(96)
    title_lines = _wrap(draw, title, title_fnt, W - 108)
    ty = 100
    for line in title_lines[:2]:
        draw.text((54, ty), line, font=title_fnt, fill=color)
        ty += 118
    draw.line([(54, ty + 12), (W - 54, ty + 12)], fill=(*color, 60), width=2)

    # 重點條列 — 每個 item 是一個卡片
    points = scene.get("points", [])
    py = ty + 60
    for i, pt in enumerate(points[:5]):
        # 卡片背景
        pt_lines = _wrap(draw, pt, fb(58), W - 200)
        card_h = max(140, len(pt_lines) * 76 + 52)
        draw.rounded_rectangle([54, py, W - 54, py + card_h], radius=16, fill=DIM)

        # 數字圓圈
        cx, cy = 54 + 52, py + card_h // 2
        draw.ellipse([cx - 36, cy - 36, cx + 36, cy + 36], fill=color)
        num_txt = str(i + 1)
        bb = draw.textbbox((0, 0), num_txt, font=fb(44))
        draw.text((cx - (bb[2]-bb[0])//2, cy - (bb[3]-bb[1])//2 - 2), num_txt, font=fb(44), fill=BG)

        # 文字
        lpy = py + (card_h - len(pt_lines) * 76) // 2
        for l in pt_lines[:2]:
            draw.text((160, lpy), l, font=fb(58), fill=WHITE)
            lpy += 76
        py += card_h + 28

    # 底部品牌
    draw.line([(0, H - 80), (W, H - 80)], fill=(*GREEN, 40), width=1)
    draw.text((54, H - 60), "@wycbotai", font=fr(36), fill=(*GREY, 180))

    sub = subtitle if subtitle is not None else scene.get("subtitle", "")
    if sub:
        _draw_subtitle(draw, sub)
    return img


def _scene_cross(data: dict, cross_type: str, subtitle: str = "") -> Image.Image:
    """
    黃金交叉 / 死亡交叉 示意圖：
    cross_type = "golden" or "death"
    """
    import math
    img, draw = _base_canvas()
    is_golden = cross_type == "golden"
    accent = GREEN if is_golden else RED
    label  = "黃金交叉" if is_golden else "死亡交叉"
    signal = "▲  買入信號" if is_golden else "▼  賣出信號"

    draw.line([(0, 8), (W, 8)], fill=accent, width=4)
    draw.text((54, 28), data["indicator_short"], font=fb(72), fill=GREEN)
    draw.text((54, 116), label, font=fb(56), fill=accent)
    draw.line([(54, 188), (W-54, 188)], fill=(*accent, 50), width=1)

    # ── 示意圖區域 ───────────────────────────────────────────────────────
    CX, CY = W // 2, 700          # 交叉點中心
    LW = 380                      # 線條半寬
    THICK = 10

    def curve_y(x, slope, base_y, curve=0.0003):
        """從交叉點往兩側彎曲"""
        return base_y + slope * x + curve * x * x

    pts_short, pts_long = [], []
    for dx in range(-LW, LW + 1, 4):
        if is_golden:
            # 黃金交叉：短期線從下穿上
            ys = curve_y(dx, -0.25,  CY, -0.0002)
            yl = curve_y(dx,  0.20,  CY,  0.0002)
        else:
            # 死亡交叉：短期線從上穿下
            ys = curve_y(dx,  0.25, CY,  0.0002)
            yl = curve_y(dx, -0.20, CY, -0.0002)
        pts_short.append((CX + dx, int(ys)))
        pts_long.append((CX  + dx, int(yl)))

    # 畫長期線（灰藍）
    for j in range(len(pts_long) - 1):
        draw.line([pts_long[j], pts_long[j+1]], fill=(100, 160, 255), width=THICK)
    # 畫短期線（金）
    for j in range(len(pts_short) - 1):
        draw.line([pts_short[j], pts_short[j+1]], fill=GOLD, width=THICK)

    # 交叉圓點
    r = 22
    draw.ellipse([CX-r, CY-r, CX+r, CY+r], fill=accent, outline=WHITE, width=3)

    # 標籤
    draw.text((CX + LW - 110, pts_short[-1][1] - 50), "短期 EMA", font=fr(38), fill=GOLD)
    draw.text((CX + LW - 110, pts_long[-1][1]  + 10), "長期 EMA", font=fr(38), fill=(100, 160, 255))

    # 方向箭頭 + 信號說明
    arrow_y = CY + (240 if is_golden else -280)
    # 框框：深色背景 + 彩色邊框，文字用白色確保可讀
    box_fill = (0, 60, 30) if is_golden else (60, 10, 10)
    draw.rounded_rectangle([120, arrow_y, W-120, arrow_y+120], radius=24,
                            fill=box_fill, outline=accent, width=4)
    bb = draw.textbbox((0,0), signal, font=fb(64))
    draw.text(((W-(bb[2]-bb[0]))//2, arrow_y+22), signal, font=fb(64), fill=WHITE)

    # 說明文字
    desc = "短期均線上穿長期均線" if is_golden else "短期均線下穿長期均線"
    desc2 = "趨勢轉強，動能向上" if is_golden else "趨勢轉弱，動能向下"
    bb2 = draw.textbbox((0,0), desc, font=fr(44))
    draw.text(((W-(bb2[2]-bb2[0]))//2, arrow_y+150), desc, font=fr(44), fill=WHITE)
    bb3 = draw.textbbox((0,0), desc2, font=fr(40))
    draw.text(((W-(bb3[2]-bb3[0]))//2, arrow_y+208), desc2, font=fr(40), fill=GREY)

    # 底部品牌
    draw.line([(0, H-80), (W, H-80)], fill=(*GREEN, 40), width=1)
    draw.text((54, H-60), "@wycbotai", font=fr(36), fill=(*GREY, 180))

    if subtitle:
        _draw_subtitle(draw, subtitle)
    return img


def _scene_cta(data: dict, subtitle: str = "") -> Image.Image:
    """CTA 結尾場景"""
    img, draw = _base_canvas()

    draw.line([(0, 8), (W, 8)], fill=GREEN, width=4)

    draw.text((54, 80),  "學會了嗎？",      font=fb(96),  fill=WHITE)
    draw.text((54, 196), "每天一個指標，",   font=fb(76),  fill=WHITE)
    draw.text((54, 292), "30天成為技術達人", font=fb(72),  fill=GREEN)
    draw.line([(54, 400), (W-54, 400)], fill=(*GREEN, 50), width=1)

    feats = [
        "AI 每日掃描 EMA / RSI / ADX 信號",
        "自動計算止損止盈比例",
        "新手也能看懂的策略報告",
    ]
    fy = 440
    for feat in feats:
        draw.text((54,  fy), ">>", font=fb(48), fill=GREEN)
        draw.text((130, fy), feat, font=fr(48), fill=WHITE)
        fy += 80

    # 留言 CTA
    draw.line([(54, fy+20), (W-54, fy+20)], fill=(*GREEN, 40), width=1)
    kw = data.get("indicator_short", "EMA")
    draw.text((54, fy+50),  "留言",          font=fr(48),  fill=GREY)
    draw.text((54, fy+110), kw,              font=fb(80),  fill=GREEN)
    draw.text((54, fy+200), "我傳策略連結給你", font=fr(48), fill=WHITE)

    # CTA 按鈕
    by = H - 340
    draw.rounded_rectangle([54, by, W-54, by+110], radius=55, fill=GREEN)
    btn_txt = "前往 wycbotai.com 免費體驗"
    bb = draw.textbbox((0,0), btn_txt, font=fb(48))
    draw.text(((W-(bb[2]-bb[0]))//2, by+28), btn_txt, font=fb(48), fill=BG)

    draw.text((54, H-200), "追蹤 @wycbotai 每天學一個指標", font=fr(40), fill=GREY)
    draw.line([(0, H-80), (W, H-80)], fill=(*GREEN, 40), width=1)
    draw.text((54, H-60), "@wycbotai", font=fr(36), fill=(*GREY, 180))

    if subtitle:
        _draw_subtitle(draw, subtitle)
    return img


# ── Claude 腳本生成 ────────────────────────────────────────────────────────────

def _generate_script(indicator_name: str) -> dict:
    client = anthropic.Anthropic()
    prompt = f"""你是台灣頂尖加密貨幣教育創作者，為 WycBotAI 生成「{indicator_name}」Reel 腳本。

目標：讓完全不懂技術分析的新手，看完 45 秒後立刻懂這個指標並想追蹤帳號
風格：口語化、有節奏感、用對比和懸念吸引人繼續看、不用術語解釋術語
語言：繁體中文，像 Podcast 主持人在說話，自然流暢

嚴格回傳 JSON，不要任何多餘文字：
{{
  "indicator_short": "指標縮寫（如 EMA）",
  "indicator_full": "指標完整中文名",
  "hook": "開場問句，讓人想繼續看（20字以內）",
  "chart_caption": "K線圖說明（20字以內）",
  "narration": "完整連貫旁白，約100-120字，自然口語，像主持人在說話，句與句之間用，或。銜接，不要分段",
  "scenes": [
    {{
      "type": "intro",
      "subtitle": "對應旁白前20字左右（直接從 narration 第一句截取）"
    }},
    {{
      "type": "chart",
      "subtitle": "對應旁白中段看圖部分（20-25字）"
    }},
    {{
      "type": "text",
      "title": "場景標題（10字以內）",
      "points": ["重點1（20字以內）", "重點2", "重點3"],
      "subtitle": "對應旁白這段的內容（20-25字）"
    }},
    {{
      "type": "text",
      "title": "常見錯誤",
      "points": ["錯誤1（20字以內）", "錯誤2", "錯誤3"],
      "subtitle": "對應旁白這段的內容（20-25字）"
    }},
    // 若指標有「黃金交叉」概念，加入這兩個場景（否則省略）：
    {{
      "type": "cross_golden",
      "subtitle": "旁白中提到黃金交叉那句話（15-20字）"
    }},
    {{
      "type": "cross_death",
      "subtitle": "旁白中提到死亡交叉那句話（15-20字）"
    }},
    {{
      "type": "cta",
      "subtitle": "對應旁白結尾呼籲行動部分（15-20字）"
    }}
  ],
  "caption": "IG 貼文文案（繁中，150-200字，含3-5個hashtag）"
}}"""

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


# ── TTS 語音生成 ───────────────────────────────────────────────────────────────

async def _tts_with_boundaries(text: str, audio_path: str, voice: str) -> list:
    """一次生成完整語音，並回傳每個詞的時間戳（秒）"""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate="-8%", pitch="+2Hz")
    boundaries = []
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append({
                    "text":   chunk["text"],
                    "offset": chunk["offset"] / 10_000_000,   # 100ns → sec
                    "end":    (chunk["offset"] + chunk["duration"]) / 10_000_000,
                })
    return boundaries


def _tts_full(narration: str, audio_path: str, voice: str) -> list:
    return asyncio.run(_tts_with_boundaries(narration, audio_path, voice))


def _audio_duration(path: str) -> float:
    from moviepy import AudioFileClip
    with AudioFileClip(path) as a:
        return a.duration


def _sentence_timings(total_dur: float, subtitles: list) -> list:
    """
    按字數比例把總時長分配給每個場景
    """
    if not subtitles:
        return []
    total_chars = sum(len(s) for s in subtitles)
    if total_chars == 0:
        dur_each = total_dur / len(subtitles)
        return [(i * dur_each, (i + 1) * dur_each) for i in range(len(subtitles))]

    timings, cursor = [], 0.0
    for s in subtitles:
        dur = total_dur * (len(s) / total_chars)
        timings.append((cursor, cursor + dur))
        cursor += dur
    return timings


# ── 動態字幕 & crossfade ──────────────────────────────────────────────────────

def _render_subtitle_at(base_img: Image.Image, boundaries: list,
                        t_global: float, fallback: str = "") -> Image.Image:
    """在 base_img 上疊加當前時刻的動態字幕（逐字跟著語音出現）"""
    img = base_img.copy()
    draw = ImageDraw.Draw(img)
    if boundaries:
        spoken = [b for b in boundaries if b["offset"] <= t_global + 0.05]
        if spoken:
            text = "".join(b["text"] for b in spoken)[-16:]  # 最近 16 個字元
            _draw_subtitle(draw, text)
    elif fallback:
        _draw_subtitle(draw, fallback)
    return img


def _apply_crossfades(scene_lists: list, n_cf: int = 10) -> list:
    """相鄰場景間做 numpy 混色轉場（取代 fade-to-black）"""
    import numpy as np
    result = list(scene_lists[0])
    for i in range(1, len(scene_lists)):
        curr = scene_lists[i]
        n = min(n_cf, len(result), len(curr))
        if n < 2:
            result.extend(curr)
            continue
        blend_base = result[-n:]
        result = result[:-n]
        for fi in range(n):
            alpha = (fi + 1) / (n + 1)
            f1 = np.array(blend_base[fi].convert("RGB")).astype(float)
            f2 = np.array(curr[fi].convert("RGB")).astype(float)
            blended = (f1 * (1 - alpha) + f2 * alpha).astype(np.uint8)
            result.append(Image.fromarray(blended))
        result.extend(curr[n:])
    return result


# ── 影片合成 ───────────────────────────────────────────────────────────────────

def _pil_to_np(img: Image.Image):
    import numpy as np
    return np.array(img.convert("RGB"))


def generate_indicator_reel(indicator_name: str = None, voice="zh-CN-YunxiNeural") -> tuple:
    """
    生成指標教學 Reel（單一連續語音 + crossfade 轉場）
    回傳 (video_path: str, caption: str)
    """
    from indicator_tutorial_gen import get_today_indicator
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, ImageSequenceClip
    from moviepy import vfx

    if indicator_name is None:
        indicator_name = get_today_indicator()

    print(f"[Reel] 生成「{indicator_name}」腳本...")
    data = _generate_script(indicator_name)
    if not data:
        raise RuntimeError("Claude 腳本生成失敗")

    scenes    = data.get("scenes", [])
    narration = data.get("narration", "。".join(s.get("subtitle","") for s in scenes))
    out_dir   = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)

    # ── 1. 一次生成完整語音 ──────────────────────────────────────────────────
    audio_path = os.path.join(out_dir, "reel_full_narration.mp3")
    print(f"[Reel] TTS 完整旁白生成中（{len(narration)} 字）...")
    boundaries = _tts_full(narration, audio_path, voice)
    total_dur = _audio_duration(audio_path)
    print(f"[Reel] WordBoundary 事件：{len(boundaries)} 個")
    print(f"[Reel] 語音總長：{total_dur:.1f} 秒")

    # ── 2. 計算每個場景的時間區段（依字數比例）──────────────────────────────────
    subtitles = [s.get("subtitle", "") for s in scenes]
    timings   = _sentence_timings(total_dur, subtitles)

    # ── 3. 建立場景片段 + crossfade 轉場 ──────────────────────────────────────
    import numpy as np
    FPS        = 24
    CHART_FPS  = 15    # chart 用較低 FPS 節省記憶體
    N_CF       = 16    # crossfade 幀數（≈0.67 秒，明顯可見）
    CHAR_SPEED = 3.0   # 字幕打字速度（字/秒）
    clips      = []
    prev_last_pil = None   # 上一個場景的最後一幀（PIL），用於 crossfade

    def _make_cf_clip(pil_a: Image.Image, pil_b: Image.Image) -> object:
        """產生 N_CF 幀的 numpy 混色 crossfade clip"""
        a = np.array(pil_a.convert("RGB")).astype(float)
        b = np.array(pil_b.convert("RGB")).astype(float)
        blend_np = []
        for fi in range(N_CF):
            alpha = (fi + 1) / (N_CF + 1)
            blend_np.append((a * (1 - alpha) + b * alpha).astype(np.uint8))
        return ImageSequenceClip(blend_np, fps=FPS)

    def _typing_clip(base_no_sub: Image.Image, subtitle: str, dur: float) -> object:
        """打字效果字幕：每秒約 CHAR_SPEED 個字逐漸出現"""
        n_chars = max(1, len(subtitle))
        frames_np = []
        base_np = _pil_to_np(base_no_sub)

        # 先無字幕停留 0.3 秒
        pause_frames = max(1, int(CHAR_SPEED * 0.3))
        frames_np.extend([base_np] * pause_frames)

        # 逐字顯示
        for n in range(1, n_chars + 1):
            frame = base_no_sub.copy()
            draw  = ImageDraw.Draw(frame)
            _draw_subtitle(draw, subtitle[:n])
            frames_np.append(_pil_to_np(frame))

        # 顯示完後繼續停留到 dur 結束
        reveal_dur  = pause_frames / CHAR_SPEED + n_chars / CHAR_SPEED
        hold_frames = max(1, int((dur - reveal_dur) * CHAR_SPEED))
        frames_np.extend([frames_np[-1]] * hold_frames)

        return ImageSequenceClip(frames_np, fps=CHAR_SPEED)

    for i, (scene, (t_start, t_end)) in enumerate(zip(scenes, timings)):
        subtitle = scene.get("subtitle", "")
        stype    = scene.get("type", "text")
        dur      = max(t_end - t_start, 1.5)

        print(f"[Reel] 場景 {i+1}/{len(scenes)}：{stype} [{t_start:.1f}s-{t_end:.1f}s]")

        if stype == "chart":
            n = max(CHART_FPS, int(dur * CHART_FPS))
            chart_pils = get_chart_frames(indicator_name, width=W-8, height=960, n_frames=n)
            np_frames_chart = []
            first_pil = last_pil = None
            for cf in chart_pils:
                base, draw = _base_canvas()
                draw.line([(0, 8), (W, 8)], fill=GREEN, width=4)
                draw.text((54, 28), data["indicator_short"], font=fb(72), fill=GREEN)
                caption_text = data.get("chart_caption", "實際K線圖解")
                draw.text((54, 116), caption_text, font=fr(44), fill=GREY)
                draw.line([(54, 174), (W-54, 174)], fill=(*GREEN, 40), width=1)
                base.paste(cf, (4, 190))
                draw.line([(0, H-80), (W, H-80)], fill=(*GREEN, 40), width=1)
                draw.text((54, H-60), "@wycbotai", font=fr(36), fill=(*GREY, 180))
                _draw_subtitle(draw, subtitle)
                if first_pil is None:
                    first_pil = base.copy()
                last_pil = base.copy()
                np_frames_chart.append(_pil_to_np(base))
            clip = ImageSequenceClip(np_frames_chart, fps=CHART_FPS)
        else:
            # 先渲染無字幕底圖，再加打字效果
            if stype == "intro":
                base_no_sub = _scene_intro(data, subtitle="")
            elif stype == "cross_golden":
                base_no_sub = _scene_cross(data, "golden", subtitle="")
            elif stype == "cross_death":
                base_no_sub = _scene_cross(data, "death", subtitle="")
            elif stype == "cta":
                base_no_sub = _scene_cta(data, subtitle="")
            else:
                color = RED if "錯誤" in scene.get("title", "") else GREEN
                base_no_sub = _scene_text(data, scene, color=color, subtitle="")

            first_pil = base_no_sub
            # 最後一幀是完整字幕的畫面（供 crossfade 使用）
            last_frame = base_no_sub.copy()
            if subtitle:
                draw = ImageDraw.Draw(last_frame)
                _draw_subtitle(draw, subtitle)
            last_pil = last_frame

            if subtitle:
                clip = _typing_clip(base_no_sub, subtitle, dur)
            else:
                clip = ImageClip(_pil_to_np(base_no_sub), duration=dur)

        # crossfade 插入
        if prev_last_pil is not None and first_pil is not None:
            cf_clip = _make_cf_clip(prev_last_pil, first_pil)
            clips.append(cf_clip)

        clips.append(clip)
        prev_last_pil = last_pil

    # ── 4. 合成視覺 ───────────────────────────────────────────────────────────
    print(f"[Reel] 合成影片（crossfade 轉場）...")
    video_only = concatenate_videoclips(clips, method="chain")
    full_audio = AudioFileClip(audio_path)
    # 音訊若比影片長則截短，短則影片延長靜音
    audio_fit  = full_audio.subclipped(0, min(full_audio.duration, video_only.duration))
    final = video_only.with_audio(audio_fit)

    video_path = os.path.join(out_dir, f"reel_{indicator_name.split('（')[0]}.mp4")
    final.write_videofile(
        video_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=os.path.join(out_dir, "temp_audio.m4a"),
        remove_temp=True,
        logger=None,
    )

    # 清理暫存
    try: os.remove(audio_path)
    except: pass

    caption = data.get("caption", f"#{indicator_name} #技術分析 #加密貨幣 #wycbotai #新手教學")
    print(f"[Reel] 完成！{video_path}")
    return video_path, caption


# ── CLI 入口 ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    name = sys.argv[1] if len(sys.argv) > 1 else "EMA（指數移動平均線）"
    video_path, caption = generate_indicator_reel(name)
    print(f"\n影片：{video_path}")
    print(f"\nCaption:\n{caption}")
