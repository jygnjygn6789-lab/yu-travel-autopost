"""
K線圖生成模組 - WycBotAI Dark Premium Style
支援 EMA / RSI / MACD / 布林帶 / 成交量 / KD 技術指標疊加
"""
from PIL import Image, ImageDraw, ImageFont
import os

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
BOLD = os.path.join(FONTS_DIR, "msjhbd.ttc")
REG  = os.path.join(FONTS_DIR, "msjh.ttc")

def fb(s): return ImageFont.truetype(BOLD, s)
def fr(s): return ImageFont.truetype(REG,  s)

BG    = (8,  13,  30)
GRID  = (25, 40,  65)
UP_C  = (0,  200, 100)
DN_C  = (220, 55, 55)
WHITE = (255, 255, 255)
GREY  = (136, 153, 170)
GOLD  = (255, 215, 0)
GREEN = (0,  255, 136)

EMA_PALETTE = {
    9:   (255, 210,   0),
    21:  ( 80, 160, 255),
    50:  (200,  80, 255),
    200: (255, 120,   0),
}

# 30 根 DOGE/USDT 4H K線 (open, high, low, close, vol)
SAMPLE_CANDLES = [
    (0.10701,0.10813,0.10564,0.10640,258294579),
    (0.10640,0.10758,0.10589,0.10708,208316480),
    (0.10709,0.10717,0.10541,0.10617,152146259),
    (0.10617,0.10689,0.10585,0.10650, 78508030),
    (0.10650,0.10985,0.10641,0.10910,317806263),
    (0.10911,0.10948,0.10793,0.10824,133133367),
    (0.10825,0.10920,0.10728,0.10885,134796019),
    (0.10884,0.11055,0.10860,0.10944,313149521),
    (0.10944,0.10972,0.10815,0.10911,126849444),
    (0.10911,0.10967,0.10772,0.10853,106302485),
    (0.10853,0.10935,0.10806,0.10816, 80447725),
    (0.10817,0.10837,0.10743,0.10791,107087036),
    (0.10792,0.10807,0.10741,0.10773, 67764301),
    (0.10774,0.10922,0.10714,0.10901,117155205),
    (0.10902,0.10936,0.10824,0.10842, 87811357),
    (0.10843,0.10920,0.10800,0.10851, 99789414),
    (0.10851,0.10858,0.10715,0.10785, 79725606),
    (0.10785,0.10826,0.10751,0.10791, 76411922),
    (0.10792,0.10881,0.10751,0.10870, 78920776),
    (0.10870,0.10940,0.10827,0.10847, 74949308),
    (0.10848,0.10879,0.10802,0.10860, 37127234),
    (0.10860,0.10966,0.10774,0.10830, 90947214),
    (0.10829,0.11383,0.10765,0.11296,469879543),
    (0.11297,0.11361,0.11102,0.11233,146484968),
    (0.11232,0.11245,0.10878,0.11050,343405909),
    (0.11049,0.11266,0.10961,0.11023,316126981),
    (0.11024,0.11161,0.10984,0.11042,107297013),
    (0.11042,0.11096,0.11000,0.11010, 56259930),
    (0.11011,0.11180,0.10996,0.11140, 67102151),
    (0.11141,0.11195,0.11124,0.11145, 87101271),
]


# ── 指標計算 ──────────────────────────────────────────────────────────────────

def _ema(closes, period):
    k = 2 / (period + 1)
    e = sum(closes[:period]) / period
    out = [None] * period + [e]
    for c in closes[period + 1:]:
        e = c * k + e * (1 - k)
        out.append(e)
    return out


def _rsi(closes, period=14):
    out = [None] * period
    for i in range(period, len(closes)):
        delta = [closes[j] - closes[j-1] for j in range(i-period+1, i+1)]
        gains  = [d for d in delta if d > 0]
        losses = [-d for d in delta if d < 0]
        ag = sum(gains)  / period if gains  else 0
        al = sum(losses) / period if losses else 1e-9
        out.append(100 - 100 / (1 + ag / al))
    return out


def _macd(closes, fast=12, slow=26, signal=9):
    ef = _ema(closes, fast)
    es = _ema(closes, slow)
    ml = [None if (ef[i] is None or es[i] is None) else ef[i] - es[i]
          for i in range(len(closes))]
    valid = [(i, v) for i, v in enumerate(ml) if v is not None]
    sig = [None] * len(closes)
    if len(valid) >= signal:
        idxs, vals = zip(*valid)
        e = sum(vals[:signal]) / signal
        sig[idxs[signal - 1]] = e
        k = 2 / (signal + 1)
        for j in range(signal, len(vals)):
            e = vals[j] * k + e * (1 - k)
            sig[idxs[j]] = e
    hist = [None if (ml[i] is None or sig[i] is None) else ml[i] - sig[i]
            for i in range(len(closes))]
    return ml, sig, hist


def _bollinger(closes, period=20, mult=2):
    upper, mid, lower = [None]*len(closes), [None]*len(closes), [None]*len(closes)
    for i in range(period - 1, len(closes)):
        w  = closes[i - period + 1: i + 1]
        m  = sum(w) / period
        sd = (sum((x - m) ** 2 for x in w) / period) ** 0.5
        mid[i]   = m
        upper[i] = m + mult * sd
        lower[i] = m - mult * sd
    return upper, mid, lower


def _stoch(candles, kp=14, dp=3):
    highs  = [c[1] for c in candles]
    lows   = [c[2] for c in candles]
    closes = [c[3] for c in candles]
    k = [None] * (kp - 1)
    for i in range(kp - 1, len(closes)):
        hh = max(highs[i - kp + 1: i + 1])
        ll = min(lows[i  - kp + 1: i + 1])
        k.append(100 * (closes[i] - ll) / (hh - ll) if hh != ll else 50)
    d = [None] * len(k)
    for i in range(dp - 1, len(k)):
        w = [k[j] for j in range(i - dp + 1, i + 1) if k[j] is not None]
        if len(w) == dp:
            d[i] = sum(w) / dp
    return k, d


# ── 繪圖工具 ──────────────────────────────────────────────────────────────────

def _draw_candles(draw, candles, width, height,
                  pad_l=8, pad_r=76, pad_t=24, pad_b=10):
    n = len(candles)
    cw_total = width - pad_l - pad_r
    ch_total = height - pad_t - pad_b
    cw = max(2, int(cw_total / n * 0.60))

    p_max = max(c[1] for c in candles) * 1.006
    p_min = min(c[2] for c in candles) * 0.994

    def cx(i): return pad_l + int((i + 0.5) * cw_total / n)
    def py(p): return pad_t + int((p_max - p) / (p_max - p_min) * ch_total)

    # grid + price labels
    for step in range(5):
        p = p_min + (p_max - p_min) * step / 4
        y = py(p)
        draw.line([(pad_l, y), (width - pad_r, y)], fill=GRID, width=1)
        draw.text((width - pad_r + 4, y - 9), f"{p:.5f}", font=fr(17), fill=GREY)

    # candles
    for i, (o, h, l, c, v) in enumerate(candles):
        x     = cx(i)
        color = UP_C if c >= o else DN_C
        draw.line([(x, py(h)), (x, py(l))], fill=color, width=2)
        y0, y1 = py(max(o, c)), py(min(o, c))
        if y1 - y0 < 2: y1 = y0 + 2
        draw.rectangle([x - cw // 2, y0, x + cw // 2, y1], fill=color)

    return cx, py, p_max, p_min


# ── 各指標圖 ──────────────────────────────────────────────────────────────────

def draw_ema_chart(candles=None, width=1080, height=640):
    candles = candles or SAMPLE_CANDLES
    n       = len(candles)
    img     = Image.new("RGB", (width, height), BG)
    draw    = ImageDraw.Draw(img)
    pad_l, pad_r = 8, 76
    cx, py, *_ = _draw_candles(draw, candles, width, height, pad_l, pad_r)
    closes     = [c[3] for c in candles]
    periods    = [9, 21]

    for period in periods:
        vals  = _ema(closes, period)
        color = EMA_PALETTE[period]
        pts   = [(cx(i), py(v)) for i, v in enumerate(vals) if v is not None]
        for j in range(len(pts) - 1):
            draw.line([pts[j], pts[j+1]], fill=color, width=3)

    # legend
    lx = pad_l + 8
    for p in periods:
        color = EMA_PALETTE[p]
        draw.line([(lx, 12), (lx + 26, 12)], fill=color, width=3)
        draw.text((lx + 30, 4), f"EMA{p}", font=fr(22), fill=color)
        lx += 100

    # golden / death cross annotations
    e9  = _ema(closes, 9)
    e21 = _ema(closes, 21)
    cw_total = width - pad_l - pad_r
    for i in range(22, n):
        if None in (e9[i], e21[i], e9[i-1], e21[i-1]): continue
        if e9[i-1] <= e21[i-1] and e9[i] > e21[i]:
            x = cx(i); y = py(candles[i][2]) - 44
            draw.line([(x, y + 32), (x, py(candles[i][2]) - 4)], fill=GREEN, width=2)
            draw.text((x - 30, y), "黃金交叉", font=fb(22), fill=GREEN)
        elif e9[i-1] >= e21[i-1] and e9[i] < e21[i]:
            x = cx(i); y = py(candles[i][1]) + 6
            draw.line([(x, py(candles[i][1]) + 2), (x, y + 22)], fill=DN_C, width=2)
            draw.text((x - 30, y + 24), "死亡交叉", font=fb(22), fill=DN_C)
    return img


def draw_rsi_chart(candles=None, width=1080, height=760):
    candles = candles or SAMPLE_CANDLES
    n       = len(candles)
    ph      = int(height * 0.62)
    rh      = height - ph - 12
    ry0     = ph + 12
    img     = Image.new("RGB", (width, height), BG)
    draw    = ImageDraw.Draw(img)
    pad_l, pad_r = 8, 76
    cx, *_ = _draw_candles(draw, candles, width, ph, pad_l, pad_r, 24, 8)
    draw.line([(0, ph + 1), (width, ph + 1)], fill=GRID, width=2)

    closes   = [c[3] for c in candles]
    rsi_vals = _rsi(closes)
    cw_total = width - pad_l - pad_r

    for level, lc in [(30, UP_C), (50, GREY), (70, DN_C)]:
        y = ry0 + int((100 - level) / 100 * rh)
        draw.line([(pad_l, y), (width - pad_r, y)], fill=GRID, width=1)
        draw.text((width - pad_r + 4, y - 9), str(level), font=fr(17), fill=lc)

    pts = [(cx(i), ry0 + int((100 - v) / 100 * rh))
           for i, v in enumerate(rsi_vals) if v is not None]
    for j in range(len(pts) - 1):
        i = j + 14
        if i < len(rsi_vals) and rsi_vals[i] is not None:
            v = rsi_vals[i]
            c = DN_C if v >= 70 else (UP_C if v <= 30 else (80, 140, 255))
            draw.line([pts[j], pts[j+1]], fill=c, width=2)

    for i, v in enumerate(rsi_vals):
        if v is None: continue
        if v >= 73:
            draw.text((cx(i) - 18, ry0 + int((100 - v) / 100 * rh) - 28),
                      "超買", font=fb(20), fill=DN_C)
        elif v <= 27:
            draw.text((cx(i) - 18, ry0 + int((100 - v) / 100 * rh) + 6),
                      "超賣", font=fb(20), fill=UP_C)

    draw.text((pad_l + 4, ry0 + 4), "RSI (14)", font=fr(22), fill=(80, 140, 255))
    return img


def draw_bollinger_chart(candles=None, width=1080, height=640):
    candles = candles or SAMPLE_CANDLES
    img  = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    pad_l, pad_r = 8, 76
    cx, py, *_ = _draw_candles(draw, candles, width, height, pad_l, pad_r)
    closes      = [c[3] for c in candles]
    upper, mid, lower = _bollinger(closes)

    for vals, color in [(upper, DN_C), (mid, GOLD), (lower, UP_C)]:
        pts = [(cx(i), py(v)) for i, v in enumerate(vals) if v is not None]
        for j in range(len(pts) - 1):
            draw.line([pts[j], pts[j+1]], fill=color, width=2)

    lx = 12
    for label, color in [("上軌", DN_C), ("中軌(MA20)", GOLD), ("下軌", UP_C)]:
        draw.line([(lx, 12), (lx + 22, 12)], fill=color, width=3)
        draw.text((lx + 26, 4), label, font=fr(22), fill=color)
        lx += 140
    return img


def draw_macd_chart(candles=None, width=1080, height=760):
    candles = candles or SAMPLE_CANDLES
    n       = len(candles)
    ph      = int(height * 0.60)
    mh      = height - ph - 12
    my0     = ph + 12
    img     = Image.new("RGB", (width, height), BG)
    draw    = ImageDraw.Draw(img)
    pad_l, pad_r = 8, 76
    cx, *_ = _draw_candles(draw, candles, width, ph, pad_l, pad_r, 24, 8)
    draw.line([(0, ph + 1), (width, ph + 1)], fill=GRID, width=2)

    closes = [c[3] for c in candles]
    ml, sig, hist = _macd(closes)
    cw_total = width - pad_l - pad_r

    hvals = [v for v in hist if v is not None]
    if not hvals: return img
    vm = max(abs(min(hvals)), abs(max(hvals))) * 1.2 or 0.001

    def vy(v): return my0 + int((vm - v) / (2 * vm) * mh)

    zero_y = vy(0)
    draw.line([(pad_l, zero_y), (width - pad_r, zero_y)], fill=GRID, width=1)

    bw = max(2, (cw_total // n) // 2)
    for i, hv in enumerate(hist):
        if hv is None: continue
        x = cx(i)
        y0, y1 = min(zero_y, vy(hv)), max(zero_y, vy(hv))
        if y1 - y0 < 1: y1 = y0 + 1
        draw.rectangle([x - bw, y0, x + bw, y1],
                       fill=UP_C if hv >= 0 else DN_C)

    for pts_src, color in [(ml, (80, 200, 255)), (sig, (255, 160, 0))]:
        pts = [(cx(i), vy(v)) for i, v in enumerate(pts_src) if v is not None]
        for j in range(len(pts) - 1):
            draw.line([pts[j], pts[j+1]], fill=color, width=2)

    lx = pad_l + 8
    for label, color in [("MACD", (80, 200, 255)), ("Signal", (255, 160, 0))]:
        draw.line([(lx, my0 + 8), (lx + 20, my0 + 8)], fill=color, width=3)
        draw.text((lx + 24, my0), label, font=fr(20), fill=color)
        lx += 110
    return img


def draw_volume_chart(candles=None, width=1080, height=760):
    candles = candles or SAMPLE_CANDLES
    n       = len(candles)
    ph      = int(height * 0.65)
    vh      = height - ph - 12
    vy0     = ph + 12
    img     = Image.new("RGB", (width, height), BG)
    draw    = ImageDraw.Draw(img)
    pad_l, pad_r = 8, 76
    cx, *_ = _draw_candles(draw, candles, width, ph, pad_l, pad_r, 24, 8)
    draw.line([(0, ph + 1), (width, ph + 1)], fill=GRID, width=2)

    vols  = [c[4] for c in candles]
    maxv  = max(vols) * 1.05
    avgv  = sum(vols) / len(vols)
    cw_total = width - pad_l - pad_r
    bw    = max(2, (cw_total // n) // 2)

    for i, (o, h, l, c, v) in enumerate(candles):
        x  = cx(i)
        bh = int(v / maxv * vh)
        y0 = vy0 + vh - bh
        base_color = UP_C if c >= o else DN_C
        color = tuple(int(x * 0.55) for x in base_color) if v < avgv else base_color
        draw.rectangle([x - bw, y0, x + bw, vy0 + vh], fill=color)

    avg_y = vy0 + vh - int(avgv / maxv * vh)
    draw.line([(pad_l, avg_y), (width - pad_r, avg_y)], fill=GOLD, width=2)
    draw.text((width - pad_r + 4, avg_y - 9), "Avg", font=fr(18), fill=GOLD)
    draw.text((pad_l + 4, vy0 + 4), "Volume", font=fr(22), fill=GREY)
    return img


def draw_kd_chart(candles=None, width=1080, height=760):
    candles = candles or SAMPLE_CANDLES
    n       = len(candles)
    ph      = int(height * 0.62)
    kh      = height - ph - 12
    ky0     = ph + 12
    img     = Image.new("RGB", (width, height), BG)
    draw    = ImageDraw.Draw(img)
    pad_l, pad_r = 8, 76
    cx, *_ = _draw_candles(draw, candles, width, ph, pad_l, pad_r, 24, 8)
    draw.line([(0, ph + 1), (width, ph + 1)], fill=GRID, width=2)

    cw_total = width - pad_l - pad_r
    def vy(v): return ky0 + int((100 - v) / 100 * kh)

    for level, lc in [(20, UP_C), (50, GREY), (80, DN_C)]:
        y = vy(level)
        draw.line([(pad_l, y), (width - pad_r, y)], fill=GRID, width=1)
        draw.text((width - pad_r + 4, y - 9), str(level), font=fr(17), fill=lc)

    kv, dv = _stoch(candles)
    for vals, color in [(kv, (80, 200, 255)), (dv, (255, 160, 0))]:
        pts = [(cx(i), vy(v)) for i, v in enumerate(vals) if v is not None]
        for j in range(len(pts) - 1):
            draw.line([pts[j], pts[j+1]], fill=color, width=2)

    draw.text((pad_l + 4,      ky0 + 4), "K", font=fr(22), fill=(80,  200, 255))
    draw.text((pad_l + 4 + 28, ky0 + 4), "D", font=fr(22), fill=(255, 160, 0))
    return img


# ── 動畫幀生成 ────────────────────────────────────────────────────────────────

def get_chart_frames(indicator_name: str, width=1072, height=720,
                     n_frames=48, start_ratio=0.2) -> list:
    """
    回傳 n_frames 張漸進顯示 K 線的 PIL Image 列表。
    每幀使用部分蠟燭插值（最後一根蠟燭從無到完整逐幀生長），
    讓動畫比單純 candle-by-candle 更順暢。
    """
    name_up = indicator_name.upper()
    candles = SAMPLE_CANDLES
    n       = len(candles)

    fn = draw_ema_chart
    for keys, f in _CHART_MAP_DATA:
        if any(k.upper() in name_up for k in keys):
            fn = f
            break

    # 起始 candle 數
    n_start = max(1, int(n * start_ratio))
    # 動畫跑完後顯示全部 candles；浮點 index 從 n_start-1 → n-1
    frames = []
    for i in range(n_frames):
        t        = i / max(n_frames - 1, 1)
        progress = t * t * (3 - 2 * t)                        # smoothstep 緩動（ease-in-out）
        f_idx    = (n_start - 1) + (n - n_start) * progress   # 浮點 candle index
        n_full   = int(f_idx)                                  # 完整顯示到第 n_full 根
        partial  = f_idx - n_full                              # 最後一根的生長比例 0~1

        n_full = min(n_full, n - 1)

        if partial > 0.01 and n_full + 1 < n:
            # 最後一根蠟燭依 partial 比例從 prev_close 往目標生長
            prev_close = candles[n_full - 1][3] if n_full > 0 else candles[0][0]
            o, h, l, c, v = candles[n_full]
            # open/close 從 prev_close 插值
            o_p = prev_close + (o - prev_close) * partial
            c_p = prev_close + (c - prev_close) * partial
            # high/low 也插值（wick 同樣跟著長）
            h_p = prev_close + (h - prev_close) * partial
            l_p = prev_close + (l - prev_close) * partial
            # 確保 OHLC 邏輯合法
            h_p = max(h_p, max(o_p, c_p))
            l_p = min(l_p, min(o_p, c_p))
            partial_candle = (o_p, h_p, l_p, c_p, int(v * partial))
            show = list(candles[:n_full]) + [partial_candle]
        else:
            show = list(candles[:n_full + 1])

        frame = fn(candles=show, width=width, height=height)
        frames.append(frame)
    return frames


_CHART_MAP_DATA = [
    (["EMA", "均線", "移動平均"],      draw_ema_chart),
    (["RSI", "強弱", "超買", "超賣"],  draw_rsi_chart),
    (["MACD", "收斂", "發散"],         draw_macd_chart),
    (["布林", "BOLLINGER"],            draw_bollinger_chart),
    (["成交量", "VOLUME"],             draw_volume_chart),
    (["KD", "隨機", "STOCH"],          draw_kd_chart),
]


# ── dispatcher ───────────────────────────────────────────────────────────────

_CHART_MAP = [
    (["EMA", "均線", "移動平均"],      draw_ema_chart),
    (["RSI", "強弱", "超買", "超賣"],  draw_rsi_chart),
    (["MACD", "收斂", "發散"],         draw_macd_chart),
    (["布林", "BOLLINGER"],            draw_bollinger_chart),
    (["成交量", "VOLUME"],             draw_volume_chart),
    (["KD", "隨機", "STOCH"],          draw_kd_chart),
]


def get_chart(indicator_name: str, width=1080, height=640) -> Image.Image:
    name_up = indicator_name.upper()
    for keys, fn in _CHART_MAP:
        if any(k.upper() in name_up for k in keys):
            return fn(width=width, height=height)
    return draw_ema_chart(width=width, height=height)
