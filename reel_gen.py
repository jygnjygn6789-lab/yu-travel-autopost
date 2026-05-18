"""
Reels 影片自動生成模組（類型 3）
精緻版：半透明卡片 + 背景音樂
使用 Pexels 高畫質圖片 + MoviePy
"""
import os
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, AudioArrayClip
from pexels import search_photos, download_image

from font_paths import FONT_BOLD, FONT_REG
SIZE = (1080, 1920)

DARK_BG      = (20, 12, 6)
WARM_ORANGE  = (210, 118, 38)
WARM_GOLD    = (192, 152, 72)
CREAM        = (248, 243, 232)
DARK_TXT     = (42, 28, 16)
LIGHT_TXT    = (200, 182, 158)
WARM_WHITE   = (255, 252, 248)

# 每個項目用不同暖色
CHECK_COLORS = [
    (210, 118, 38),
    (62, 148, 142),
    (168, 88, 130),
    (88, 140, 80),
    (138, 100, 178),
]


def fb(size): return ImageFont.truetype(FONT_BOLD, size)
def fr(size): return ImageFont.truetype(FONT_REG, size)


def shadow(draw, xy, text, fnt, color=WARM_WHITE):
    x, y = xy
    draw.text((x+3, y+3), text, font=fnt, fill=(0, 0, 0, 200))
    draw.text(xy, text, font=fnt, fill=color)


def center_r(draw, y, text, fnt, color=WARM_WHITE):
    bb = draw.textbbox((0, 0), text, font=fnt)
    x = (SIZE[0] - (bb[2] - bb[0])) // 2
    shadow(draw, (x, y), text, fnt, color)


def wrap_text(text, font, max_w, draw):
    lines, cur = [], ""
    for ch in text:
        test = cur + ch
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def gradient_bg(img, top_a=0, bot_a=230):
    ov = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(SIZE[1]):
        t = (y / SIZE[1]) ** 1.6
        a = int(top_a + (bot_a - top_a) * t)
        d.line([(0, y), (SIZE[0], y)], fill=(18, 10, 4, a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def darken(img, a=110):
    ov = Image.new("RGBA", SIZE, (20, 12, 5, a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def ov_rect(img, box, fill_rgba):
    rgba = img.convert("RGBA")
    ov = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle(box, fill=fill_rgba)
    return Image.alpha_composite(rgba, ov).convert("RGB")


def ov_rounded(img, box, radius, fill_rgba):
    rgba = img.convert("RGBA")
    ov = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(box, radius=radius, fill=fill_rgba)
    return Image.alpha_composite(rgba, ov).convert("RGB")


def cream_panel(img, y0, y1, alpha=210):
    """奶油色半透明面板"""
    return ov_rounded(img, [44, y0, SIZE[0]-44, y1], 18, (*CREAM, alpha))


def footer_tag(img):
    img = ov_rect(img, [0, SIZE[1] - 90, SIZE[0], SIZE[1]], (12, 7, 2, 190))
    draw = ImageDraw.Draw(img)
    draw.text((60, SIZE[1] - 74), "@taiwan.travel.deals", font=fr(36), fill=LIGHT_TXT)
    draw.text((SIZE[0]-218, SIZE[1]-74), "主頁連結 >>", font=fr(36), fill=(*WARM_GOLD, 220))
    return img


def tag_pill(img, x, y, text, fnt, bg_color=None):
    bg_color = bg_color or WARM_ORANGE
    tmp_d = ImageDraw.Draw(img)
    bb = tmp_d.textbbox((0, 0), text, font=fnt)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    img = ov_rounded(img, [x, y, x + tw + 36, y + th + 20], 22, (*bg_color, 225))
    draw = ImageDraw.Draw(img)
    draw.text((x + 18, y + 10), text, font=fnt, fill=WARM_WHITE)
    return img, x + tw + 36


def eng_bar(img, y):
    """互動引導橫條"""
    img = ov_rect(img, [0, y, SIZE[0], y + 70], (20, 12, 5, 190))
    draw = ImageDraw.Draw(img)
    txt = "按讚  |  追蹤  |  留言城市名取得攻略"
    bb = draw.textbbox((0, 0), txt, font=fr(30))
    ex = (SIZE[0] - (bb[2]-bb[0])) // 2
    draw.text((ex, y + 16), txt, font=fr(30), fill=(220, 200, 175))
    return img


# ── Scene builders (暖色極簡風，對標 @liketravel_official) ───────────────────

def scene_cover(bg: Image.Image, label: str, name: str, subtitle: str = "") -> np.ndarray:
    """封面：極簡大字 hook，暖色調"""
    img = darken(bg, 95)
    img = gradient_bg(img, 0, 210)

    # 標籤
    img, _ = tag_pill(img, 60, 500, f"  \\ {label} /  ", fb(58))

    # 大景點名（垂直置中偏下）
    draw = ImageDraw.Draw(img)
    bb = draw.textbbox((0, 0), name, font=fb(152))
    tw = bb[2] - bb[0]
    x = (SIZE[0] - tw) // 2
    shadow(draw, (x, 600), name, fb(152), WARM_WHITE)

    if subtitle:
        center_r(draw, 810, subtitle, fb(56), LIGHT_TXT)

    # 裝飾線
    cx = SIZE[0] // 2
    draw.line([(cx-180, 912), (cx-20, 912)], fill=(*WARM_GOLD, 200), width=3)
    draw.ellipse([cx-12, 904, cx+12, 920], fill=(*WARM_GOLD, 220))
    draw.line([(cx+20, 912), (cx+180, 912)], fill=(*WARM_GOLD, 200), width=3)

    # swipe hint
    img = ov_rect(img, [0, 1260, SIZE[0], 1355], (15, 9, 3, 170))
    draw = ImageDraw.Draw(img)
    center_r(draw, 1274, "往上滑看更多", fr(46), LIGHT_TXT)

    img = eng_bar(img, SIZE[1] - 160)
    img = footer_tag(img)
    return np.array(img)


def scene_info(bg: Image.Image, title: str, items: list) -> np.ndarray:
    """亮點：奶油面板 + D圈圈"""
    img = darken(bg, 130)
    img = gradient_bg(img, 60, 220)

    draw = ImageDraw.Draw(img)
    draw.text((60, 55), "@taiwan.travel.deals", font=fr(36), fill=(*LIGHT_TXT, 180))

    # 標題
    img, _ = tag_pill(img, 60, 120, f"  {title}  ", fb(60), WARM_ORANGE)
    draw = ImageDraw.Draw(img)

    # 奶油面板
    panel_y = 240
    panel_h = 1340
    img = cream_panel(img, panel_y, panel_y + panel_h, 210)

    # 項目均分於面板
    n = min(len(items), 4)
    slot = panel_h // n if n else 335

    for i, item in enumerate(items[:4]):
        col = CHECK_COLORS[i % len(CHECK_COLORS)]
        item_top = panel_y + i * slot + 20
        card_mid = item_top + slot // 2 - 30

        draw_tmp = ImageDraw.Draw(img)
        lines = wrap_text(item, fb(50), 830, draw_tmp)
        text_h = len(lines) * 66

        # 彩色圓點
        img = ov_rounded(img, [72, card_mid+8, 92, card_mid+28], 10, (*col, 240))
        draw = ImageDraw.Draw(img)

        text_start = card_mid - text_h // 2 + 20
        for j, line in enumerate(lines):
            draw.text((112, text_start + j * 66), line, font=fb(50), fill=DARK_TXT)

        # 分隔線
        if i < n - 1:
            sep_y = panel_y + (i + 1) * slot + panel_y // 10
            draw.line([(70, sep_y), (SIZE[0]-70, sep_y)], fill=(*CREAM, 100), width=1)

    img = eng_bar(img, SIZE[1] - 160)
    img = footer_tag(img)
    return np.array(img)


def scene_transport(bg: Image.Image, route: str, station: str, walk: str) -> np.ndarray:
    """交通：奶油面板 + emoji 行"""
    img = darken(bg, 140)
    img = gradient_bg(img, 50, 215)

    draw = ImageDraw.Draw(img)
    draw.text((60, 55), "@taiwan.travel.deals", font=fr(36), fill=(*LIGHT_TXT, 180))

    img, _ = tag_pill(img, 60, 120, "  交通方式  ", fb(60), (62, 148, 142))

    rows = [
        ("路線", "搭乘路線", route,   (62, 148, 142)),
        ("下車", "下車站",   station, WARM_ORANGE),
        ("步行", "步行時間", walk,    (138, 100, 178)),
    ]
    active = [(e, l, v, c) for e, l, v, c in rows if v]
    n = len(active)

    panel_y = 240
    panel_h = 1340
    img = cream_panel(img, panel_y, panel_y + panel_h, 210)
    slot = panel_h // n if n else 445

    for i, (emoji, label, val, col) in enumerate(active):
        item_mid = panel_y + i * slot + slot // 2

        draw_tmp = ImageDraw.Draw(img)
        val_lines = wrap_text(val, fr(50), 830, draw_tmp)

        # 大 emoji
        draw = ImageDraw.Draw(img)
        shadow(draw, (70, item_mid - 110), emoji, fb(90), col)

        # label
        draw.text((180, item_mid - 108), f"{label}：", font=fb(52), fill=col)

        # 值
        val_h = len(val_lines) * 62
        vy = item_mid - 20
        for j, line in enumerate(val_lines):
            draw.text((80, vy + j * 62), line, font=fr(50), fill=DARK_TXT)

        if i < n - 1:
            sep_y = panel_y + (i+1)*slot
            draw.line([(70, sep_y), (SIZE[0]-70, sep_y)], fill=(*CREAM, 100), width=1)

    img = eng_bar(img, SIZE[1] - 160)
    img = footer_tag(img)
    return np.array(img)


def scene_cta(bg: Image.Image, name: str) -> np.ndarray:
    """結尾 CTA：大字 + 按鈕"""
    img = darken(bg, 160)
    img = gradient_bg(img, 60, 230)

    # 奶油光暈
    img = ov_rounded(img, [80, 440, SIZE[0]-80, 1360], 36, (*CREAM, 45))

    draw = ImageDraw.Draw(img)
    shadow(draw, ((SIZE[0] - draw.textbbox((0,0),name,font=fb(140))[2])//2, 500),
           name, fb(140), WARM_WHITE)

    cx = SIZE[0] // 2
    for w in [60, 140, 230]:
        a = max(20, 140 - w)
        draw.line([(cx-w, 710), (cx+w, 710)], fill=(*WARM_GOLD, a), width=1)

    center_r(draw, 760, "完整攻略 + 最低機票", fb(58), WARM_GOLD)
    center_r(draw, 858, "優惠都在主頁！", fb(58), WARM_GOLD)

    # 按鈕
    btn_txt = "點主頁連結立即查看"
    img = ov_rounded(img, [120, 990, SIZE[0]-120, 1110], 48, (*WARM_ORANGE, 225))
    draw = ImageDraw.Draw(img)
    bb = draw.textbbox((0, 0), btn_txt, font=fb(56))
    bx = (SIZE[0] - (bb[2]-bb[0])) // 2
    draw.text((bx, 1008), btn_txt, font=fb(56), fill=WARM_WHITE)

    img = eng_bar(img, SIZE[1] - 160)
    img = footer_tag(img)
    return np.array(img)


def frames_to_clip(frame: np.ndarray, duration: float, zoom: bool = True) -> ImageClip:
    clip = ImageClip(frame).with_duration(duration)
    if zoom:
        clip = clip.resized(lambda t: 1 + 0.025 * t / duration)
    return clip


# ── Background music ──────────────────────────────────────────────────────────

BGM_DIR = os.path.join(os.path.dirname(__file__), "bgm")


def _find_bgm() -> str | None:
    """在 bgm/ 資料夾中找第一個音樂檔案"""
    if not os.path.isdir(BGM_DIR):
        return None
    for name in os.listdir(BGM_DIR):
        if name.lower().endswith((".mp3", ".wav", ".aac", ".m4a")):
            return os.path.join(BGM_DIR, name)
    return None


def _pluck(freq: float, dur: float, sr: int = 44100, decay: float = 0.995) -> np.ndarray:
    """Karplus-Strong 撥弦合成（吉他/豎琴音色）"""
    n = max(2, int(sr / freq))
    buf = np.random.randn(n) * 0.9
    total = int(sr * dur)
    out = np.zeros(total)
    for i in range(total):
        out[i] = buf[0]
        avg = decay * 0.5 * (buf[0] + buf[1])
        buf = np.roll(buf, -1)
        buf[-1] = avg
    return out


def _make_ambient_tone(duration: float, sr: int = 44100) -> AudioArrayClip:
    """生成旅行感撥弦背景音樂（吉他 + 豎琴和弦）"""
    total = int(sr * duration)
    track = np.zeros(total)

    # 和弦進行 C → Am → F → G 循環
    chords = [
        [261.63, 329.63, 392.00],   # C major
        [220.00, 261.63, 329.63],   # A minor
        [174.61, 220.00, 261.63],   # F major
        [196.00, 246.94, 293.66],   # G major
    ]
    beat = total // (len(chords) * 2)
    for repeat in range(2):
        for ci, chord in enumerate(chords):
            t0 = (repeat * len(chords) + ci) * beat
            for freq in chord:
                seg = _pluck(freq, beat / sr * 1.5, sr)
                end = min(t0 + len(seg), total)
                track[t0:end] += seg[:end - t0] * 0.30

    # 高音旋律（豎琴撥弦）
    melody_freqs = [523.25, 587.33, 659.25, 784.00, 698.46, 659.25, 587.33, 523.25]
    note_len = total // len(melody_freqs)
    for i, freq in enumerate(melody_freqs):
        t0 = i * note_len
        seg = _pluck(freq, note_len / sr * 0.9, sr, decay=0.998)
        end = min(t0 + len(seg), total)
        track[t0:end] += seg[:end - t0] * 0.22

    # Normalize 到 0.75
    mx = np.max(np.abs(track))
    if mx > 0:
        track = track / mx * 0.75

    # 淡入淡出
    fade = int(sr * 1.0)
    if fade < total:
        track[:fade] *= np.linspace(0, 1, fade)
        track[-fade:] *= np.linspace(1, 0, fade)

    stereo = np.column_stack([track, track])
    return AudioArrayClip(stereo, fps=sr)


def attach_bgm(video, total_duration: float):
    """為影片加上背景音樂（BGM 檔或環境音）"""
    bgm_path = _find_bgm()
    if bgm_path:
        try:
            audio = AudioFileClip(bgm_path).with_duration(total_duration).with_volume_scaled(0.35)
            print(f"[BGM] 使用音樂檔：{os.path.basename(bgm_path)}")
            return video.with_audio(audio)
        except Exception as e:
            print(f"[BGM] 音樂檔讀取失敗，改用環境音：{e}")
    else:
        print(f"[BGM] 未找到 bgm/ 資料夾音樂，使用環境音。如需真實 BGM 請將 .mp3 放入 {BGM_DIR}")

    audio = _make_ambient_tone(total_duration)
    return video.with_audio(audio)


# ── 對外介面 ──────────────────────────────────────────────────────────────────

def generate_spot_reel(
    spot_name: str,
    location: str,
    label: str,
    highlights: list,
    transport: dict,
    output_path: str = None,
) -> str:
    """
    生成景點 Reels 影片（含背景音樂）
    回傳本地 .mp4 路徑
    """
    print(f"[Reel] 開始生成：{spot_name}")

    queries = [
        f"{location} {spot_name}",
        f"{location} travel scenic",
        f"{location} street food local",
        f"{location} tourist attraction",
    ]
    bgs = []
    for q in queries:
        urls = search_photos(q, count=1, orientation="portrait")
        if urls:
            bgs.append(download_image(urls[0], SIZE))
        if len(bgs) >= 4:
            break
    while len(bgs) < 4:
        bgs.append(bgs[0] if bgs else Image.new("RGB", SIZE, DARK_BG))

    f1 = scene_cover(bgs[0], label, spot_name, location)
    f2 = scene_info(bgs[1], "必看亮點", highlights[:4])
    f3 = scene_transport(bgs[2],
                          transport.get("route", ""),
                          transport.get("station", ""),
                          transport.get("walk", ""))
    f4 = scene_cta(bgs[3], spot_name)

    durations = [3.5, 4.0, 3.5, 3.0]
    clips = [frames_to_clip(f, d) for f, d in zip([f1, f2, f3, f4], durations)]
    total_dur = sum(durations)

    video = concatenate_videoclips(clips, method="compose")
    video = attach_bgm(video, total_dur)

    if not output_path:
        output_path = os.path.join(
            os.path.dirname(__file__), "output",
            f"reel_{spot_name}_{int(time.time())}.mp4".replace(" ", "_")
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"[Reel] 輸出影片：{output_path}")
    video.write_videofile(output_path, fps=30, codec="libx264",
                          audio_codec="aac", logger=None)
    print(f"[Reel] 完成！")
    return output_path
