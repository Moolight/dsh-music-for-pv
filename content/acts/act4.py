"""Act 8 -- Bridge, lines 77-91 (182.64-225.74 s), shots S41-S51.

The Bridge is the longest single block in the song (43.10 s, 15 lyric lines,
11 shots) and the emotional reversal of the film:

    mouthing off (S41-S43) -> caught being cute (S44-S45) -> admits the round
    thing (S46-S47) -> softens (S48-S49) -> promise (S50-S51)

Rhythm notes that drive every choice below:
  * roughly one shot per 2-7 s, i.e. far slower than a beat per cut. Inside a
    shot the frame holds still and ONE element moves per lyric clause, so the
    cut is the event and the motion is only the punctuation.
  * S50's line 90 is the "semantic pivot" exception: the whole sentence is
    decoded out of noise in one pass instead of being karaoke-highlighted,
    because the viewer has to read it as a complete thought.
  * S51 is one of the film's three "breathing holes": 2.84 s of stillness. No
    flicker, no displacement, no cut -- the water keeps frozen geometry and only
    its brightness breathes. The single blue point is the film-wide heartbeat
    cursor (M7, 1.21 s = two beats at quarter = 99).

Brand blue stays hers: her body, the rim light, the heartbeat cursor, the rice
cake. System furniture (racks, panels, the dialogue box, the sea) is cold steel.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from pvlib.kit import *

# shotkit re-exports BLUE (== kit.BLUE_MID) but not the text blues, and this act
# needs all three: BLUE_MID for things she makes, BLUE_TEXT whenever Chinese has
# to be read on top of them.
BLUE_MID = kit.BLUE_MID
BLUE_TEXT = kit.BLUE_TEXT

# ...and the two smoothstep easings live in tuikit, not in the shotkit namespace.
smooth = kit.smooth
ease = kit.ease

# ---------------------------------------------------------------- small tools

_FONT_CACHE: dict = {}


def gfont(size: int) -> ImageFont.FreeTypeFont:
    f = _FONT_CACHE.get(size)
    if f is None:
        f = ImageFont.truetype(kit.F_CJK, size)
        _FONT_CACHE[size] = f
    return f


def noise_glyph(i: int, seed: int) -> str:
    """Deterministic ASCII stand-in for a hanzi that has not settled yet. The
    whole-line decodes need per-character noise and `kit.decode` only speaks
    monospace, so this keeps hashed-per-index determinism in the CJK face."""
    r = random.Random((seed * 1000003) ^ (i * 7919))
    return r.choice("!<>-_\\/[]{}=+*^?#%$&@01|~;:")


def decode_cjk(img: Image.Image, s: str, at: float, t: float, cx: float, y: float,
               size: int = SZ_TITLE, fill=None, rate: float = 9.0, seed: int = 0,
               glow: float = 0.0) -> None:
    """Whole-sentence decode, done as one graphic rather than per glyph.

    Before `at` nothing is drawn (the element rises out of the void); while it
    settles each character flickers through ASCII noise; once settled it sits
    still. `cx`/`y` is the centre of the first line, in pixels.
    """
    if t < at:
        return
    age = t - at
    f = gfont(size)
    shown, sharp = [], []
    for i, ch in enumerate(s):
        a = age * rate - i
        if a <= 0:
            break
        shown.append(noise_glyph(i, seed) if (a < 0.14 and ch != " ") else ch)
        sharp.append(ch if a >= 0.14 else " ")
    if not shown:
        return
    disp, real = "".join(shown), "".join(sharp)
    w = f.getlength(s)
    x = cx - w / 2
    col = fill if fill is not None else kit.BLUE_TEXT
    if glow > 0:
        pad = 26
        lay = Image.new("RGBA", (int(w) + 2 * pad, size + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((pad, pad), real, font=f, fill=(255, 255, 255, 255))
        lay = lay.filter(ImageFilter.GaussianBlur(2.4))
        a = lay.getchannel("A").point(lambda v: min(255, int(v * glow)))
        img.paste(Image.new("RGB", lay.size, kit.BLUE_MID),
                  (int(x) - pad, int(y) - pad), a)
    ImageDraw.Draw(img).text((x, y), disp, font=f, fill=col)


def rim_of(a: Image.Image, k: int) -> Image.Image:
    """The bright edge of a silhouette's alpha: a selection outline, which is how
    the film draws "her skeleton" without needing another asset."""
    k = max(1, int(k))
    thick = a.filter(ImageFilter.MaxFilter(2 * k + 1))
    thin = a.filter(ImageFilter.MaxFilter(3))
    r = ImageChops.difference(thick, thin)
    if k == 1:
        r = ImageChops.difference(thick, a)
    return r


def outline_sp(spr: Image.Image, k: int, color, level: float) -> Image.Image:
    a = spr.getchannel("A")
    rim = rim_of(a, k)
    out = Image.new("RGBA", spr.size, tuple(color) + (255,))
    out.putalpha(rim.point(lambda v: int(v * level)))
    return out


def hand(d, x: float, y: float, w: float = 62, h: float = 40, u: float = 1.0,
         tilt: float = 0.0, level: float = 0.5) -> None:
    """A hand without a hand asset: three half-block cells in a row, the middle
    knuckle taller. Reads as "something reached in from off-frame"."""
    lv = level * clamp01(u)
    if lv <= 0.01:
        return
    ex = math.cos(tilt)
    for dx, dy, ww, hh in ((-0.42, 0.10, 0.30, 0.86), (0.0, 0.0, 0.34, 1.0),
                           (0.40, 0.12, 0.28, 0.80)):
        cx = x + dx * w * ex
        cy = y + dy * h
        d.rectangle([cx - ww * w / 2, cy - hh * h / 2, cx + ww * w / 2, cy + hh * h / 2],
                    fill=kit.mix(STEEL, 0.30 + 0.26 * lv))
    d.rectangle([x - 0.62 * w, y - 0.5 * h, x + 0.62 * w, y - 0.34 * h],
                fill=kit.mix(STEEL, 0.22 + 0.24 * lv))


def whale_bits() -> Image.Image:
    """The real-whale silhouette (M3), built from primitives: flukes, peduncle,
    fat body, pectoral fin, jaw. Pure shape -- no maid dress, no hairband. This
    is "what she actually is", and S51 reuses it verbatim from S36."""
    S = 4
    ss = 440 * S
    im = Image.new("L", (ss, int(ss * 0.46)), 0)
    dd = ImageDraw.Draw(im)

    def E(cx, cy, rx, ry):
        dd.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=255)

    def P(pts):
        dd.polygon([(x * S, y * S) for x, y in pts], fill=255)

    P([(88, 62), (46, 14), (28, 18), (44, 46), (8, 38), (4, 58), (16, 64),
       (2, 76), (10, 96), (46, 78), (24, 84), (30, 64)])          # flukes
    P([(122, 50), (94, 64), (150, 96), (198, 110), (198, 58)])     # peduncle
    E(300, 92, 98, 46)                                             # body
    E(394, 100, 44, 31)                                            # head
    P([(416, 90), (438, 96), (440, 112), (414, 124)])              # jaw
    P([(328, 118), (370, 132), (344, 180), (312, 152)])            # pectoral fin
    return im.filter(ImageFilter.GaussianBlur(S * 0.8)).point(lambda v: 255 if v > 110 else 0)


_WHALE = None


def whale_sil(w: int, color=STEEL, rim=BLUE_MID, level: float = 1.0) -> Image.Image:
    """Silhouette with a halftone interior: at full opacity a pale whale reads as
    a sticker pasted over the sea, so the body keeps the same cell grid the rest
    of the TUI world is made of and stays translucent."""
    global _WHALE
    if _WHALE is None:
        _WHALE = whale_bits()
    k = w / _WHALE.width
    small = _WHALE.resize((max(2, int(_WHALE.width * k)), max(2, int(_WHALE.height * k))),
                          Image.LANCZOS)
    edge = ImageChops.difference(small.filter(ImageFilter.MaxFilter(3)), small)
    a = ImageChops.multiply(small, kit.grid_mask(small.width, small.height, 4))
    out = Image.new("RGBA", small.size, tuple(color) + (0,))
    out.putalpha(a.point(lambda v: int(v * 0.42 * level)))
    gl = Image.new("RGBA", small.size, tuple(rim) + (0,))
    gl.putalpha(edge.point(lambda v: int(v * 0.85 * level)))
    out.alpha_composite(gl)
    return out


def rack_col(d, x: int, y0: int, y1: int, seed: int, t: float, level: float = 0.5) -> None:
    """A column of server-rack status lights, still breathing at the film's rate.
    The rack is only the room she is standing in; it never becomes the subject."""
    r = random.Random(seed)
    n = (y1 - y0) // 26
    for i in range(n):
        r.random()
        base = (0.30 + 0.22 * pulse(t + i * 0.31, HEART)) * r.uniform(0.7, 1.15)
        kit.heat_cell(d, x, y0 + i * 26, 15, 20, base * level / 0.5, color=STEEL)


def water_bands(d, t: float, top: int, bottom: int, bright: float = 1.0,
                frozen: bool = True, n: int = 26) -> None:
    """Horizontal luminance bands standing in for the surface seen from below.
    With `frozen` the geometry is a function of the band index alone, so nothing
    travels -- only the shade breathes, which is exactly what S51 needs."""
    for i in range(n):
        u = i / (n - 1)
        y = int(top + (bottom - top) * (u ** 1.35))
        h = 3 + int(10 * u)
        swell = (math.sin(i * 1.7 + 0.6) if frozen
                 else math.sin(i * 1.7 + 0.6 + t * 0.55))
        v = (0.10 + 0.30 * u) * (0.55 + 0.45 * swell) * bright
        v *= 0.88 + 0.12 * pulse(t * 0.28 + i * 0.05, 6.0) if frozen else 1.0
        d.rectangle([0, y, W, y + h], fill=kit.mix(STEEL, clamp01(v) * 0.55))
        d.line([0, y, W, y], fill=kit.mix(STEEL, clamp01(v * 1.3)))


def desk(d, x0: int, y0: int, x1: int, y1: int, level: float = 0.5) -> None:
    d.rectangle([x0, y0, x1, y1], outline=kit.mix(STEEL, level))
    d.line([x0, y0 + 3, x1, y0 + 3], fill=kit.mix(STEEL, level * 1.4))


def bowl(d, cx: float, cy: float, r: float, level: float = 0.6, rice: bool = True) -> None:
    """The rice bowl (M2). From straight above it is ellipses and a scoop."""
    d.ellipse([cx - r, cy - r * 0.78, cx + r, cy + r * 0.78], outline=kit.mix(STEEL, level))
    if rice:
        for i in range(3):
            rr = r * (0.72 - i * 0.19)
            d.ellipse([cx - rr, cy - rr * 0.72, cx + rr, cy + rr * 0.72],
                      outline=kit.mix(STEEL, level * (0.75 - i * 0.14)))
        kit.heat_cell(d, cx - r * 0.26, cy - r * 0.22, r * 0.5, r * 0.42, 0.55, color=STEEL)


def chair(d, cx: float, cy: float, w: float, solid: float = 0.0, level: float = 0.5) -> None:
    """An empty chair, block-out simple. `solid` fades the dashed frame into a
    solid one -- the moment a hand holds it, the way a promise stops being a
    suggestion."""
    h = w * 1.05
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    bars = ((x0, y0, x0, y1), (x1, y0, x1, y1), (x0, y0, x1, y0), (x0, y1, x1, y1))
    if solid < 0.999:
        lv = level * (1.0 - solid)
        for a in bars:
            ln = math.hypot(a[2] - a[0], a[3] - a[1])
            n = max(2, int(ln / 9))
            for i in range(0, n, 2):
                p, q = i / n, (i + 1) / n
                d.line([a[0] + (a[2] - a[0]) * p, a[1] + (a[3] - a[1]) * p,
                        a[0] + (a[2] - a[0]) * q, a[1] + (a[3] - a[1]) * q],
                       fill=kit.mix(STEEL, lv))
    if solid > 0.001:
        for a in bars:
            d.line(list(a), fill=kit.mix(STEEL, level * solid))
    d.line([x0 + 4, cy - h * 0.06, x1 - 4, cy - h * 0.06], fill=kit.mix(STEEL, level * max(solid, 0.35)))
    d.line([x0 + 4, y0 + h * 0.24, x1 - 4, y0 + h * 0.24], fill=kit.mix(STEEL, level * max(solid, 0.35)))


def mochi(d, cx: float, cy: float, r: float, level: float) -> None:
    """The rice-cake node the tail note collapses into: nested rings, blue core."""
    if level <= 0.02 or r <= 1:
        return
    for i, k in enumerate((1.0, 0.74, 0.48)):
        d.ellipse([cx - r * k, cy - r * k * 0.86, cx + r * k, cy + r * k * 0.86],
                  outline=kit.mix(BLUE_TEXT, level * (0.9 - i * 0.16)))
    d.ellipse([cx - r * 0.30, cy - r * 0.28, cx + r * 0.30, cy + r * 0.28],
              fill=kit.mix(BLUE_MID, 0.52 * level))


# ================================================================ S41
def draw_s41(img, d, t, s):
    """77 我不是胖 是蓝鲸骨架大  (182.64-185.92, 3.28 s)

    She stands in the rack room and a selection outline is traced around her --
    the "skeleton". It widens one cell the moment 大 lands, which is the whole
    joke: the outline is her alibi, not her body."""
    u = s.u(t)
    rack_col(d, 84, 150, 700, 11, t, 0.30)
    rack_col(d, 1181, 150, 700, 12, t, 0.30)
    d.line([0, 598, W, 598], fill=kit.mix(STEEL, 0.10))

    spr = sprite("serious", "bust", 460, 520)
    px, py = 640, 598 - spr.height
    img.paste(spr, (int(px - spr.width / 2), int(py)), spr)

    big = 1.0 + 0.55 * smooth(clamp01((t - 184.90) / 0.55))
    rim = outline_sp(spr, int(round(2 + 4 * (big - 1) / 0.55)), BLUE_MID, 0.40 + 0.12 * u)
    img.paste(rim, (int(px - spr.width / 2), int(py)), rim)

    mw = spr.width * big * 0.5
    yy = int(py + spr.height * 0.34)
    d.line([px - mw, yy, px - mw, yy + 12], fill=kit.mix(BLUE_TEXT, 0.62))
    d.line([px + mw, yy, px + mw, yy + 12], fill=kit.mix(BLUE_TEXT, 0.62))
    d.line([px - mw, yy + 6, px + mw, yy + 6], fill=kit.mix(BLUE_TEXT, 0.38))
    cjk_text(d, (px + mw + 12, yy - 8), "%d px" % int(mw * 2), SZ_MIN, kit.mix(BLUE_TEXT, 0.85))

    dec(d, (56, 636), "SKELETON: blue-whale grade", 182.64, t, size=15, level=0.62, rate=26)
    slab_text(d, (56, 664), "骨架 / not fat", SZ_BODY, kit.mix(STEEL, 0.95))
    caption(d, (W - 276, 668), "bridge 01/11", 14, 0.35)


# ================================================================ S42
def draw_s42(img, d, t, s):
    """78 我不是懒 是在思考人生啊  (185.92-188.24, 2.32 s)

    A thinking ring turns above her head at a crawl; on 啊 it stops dead and a
    question mark drops out of it. The field is deliberately silent -- she has
    really stopped, so the dots stop with her."""
    u = s.u(t)
    rack_col(d, 84, 150, 700, 11, t, 0.20)
    rack_col(d, 1181, 150, 700, 12, t, 0.20)
    d.line([0, 598, W, 598], fill=kit.mix(STEEL, 0.08))
    if u > 0.30:
        d.rectangle([0, 556, W, 596], fill=kit.BG)      # the field is quiet

    spr = sprite("confused", "bust", 440, 500)
    px, py = 640, 598 - spr.height
    img.paste(spr, (int(px - spr.width / 2), int(py)), spr)

    a = 187.94                       # the 啊
    cx, cy, R = 640, 150, 70
    turns = (min(t, a) - 185.92) * 0.42
    for i in range(30):
        du = i / 29.0
        ang = turns * 2 * math.pi + du * 5.6
        rr = R * (0.30 + 0.70 * du)
        x = cx + math.cos(ang - 1.5708) * rr
        y = cy + math.sin(ang - 1.5708) * rr * 0.62
        d.rectangle([x, y, x + 3, y + 3], fill=kit.mix(STEEL, (0.18 + 0.82 * du) * 0.85))
    d.rectangle([cx - 2, cy - 2, cx + 2, cy + 2],
                fill=kit.mix(BLUE_TEXT, 0.55 + 0.45 * heartbeat(t)))
    caption(d, (cx + 88, cy - 8), "thinking" + "." * (1 + int((t - 185.92) / 0.9)), 16, 0.6)
    if t >= a:
        fall = clamp01((t - a) / 0.30)
        slab_text(d, (cx - 10, cy + 44 + 46 * fall * fall), "?", 22,
                  kit.mix(BLUE_TEXT, 0.9), pad=4)

    slab_text(d, (56, 664), "停下来了", SZ_BODY, kit.mix(STEEL, 0.9))
    caption(d, (W - 276, 668), "bridge 02/11", 14, 0.35)


# ================================================================ S43
def draw_s43(img, d, t, s):
    """79 鲸鳍一甩 鲸尾一拍 / 80 你才大肥鱼 你全家大肥鱼  (188.24-195.64, 7.40 s)

    The one place in the song the emotion goes outward. One move per clause:
    fin swipe (with an afterimage that hangs half a second), tail slap (the whole
    field jolts one cell and rebounds), then the push-in onto the spiky face and
    three struck-through 大肥鱼 labels."""
    u = s.u(t)
    jolt = 0.0
    if 190.30 <= t < 190.86:
        v = (t - 190.30) / 0.56
        jolt = -18 * math.exp(-7 * v) * math.cos(26 * v)
    img.paste(field(), (6, int(jolt)))
    d.rectangle([0, 0, W, 6], fill=kit.BG)
    rack_col(d, 84, 150, 700, 11, t, 0.16)
    rack_col(d, 1181, 150, 700, 12, t, 0.16)

    push = smooth(clamp01((t - 191.50) / 1.15))
    face = t >= 190.92
    w0 = int(600 * (1 + 0.06 * smooth(clamp01((t - 190.92) / 0.22))))
    spr = sprite("frightened" if face else "serious", "bust", w0, 700)
    if push > 0.01:
        k = 1 + 0.40 * push
        spr = spr.resize((max(2, int(spr.width * k)), max(2, int(spr.height * k))), Image.LANCZOS)
    px = (640 + 70 * push) if face else 640
    py = ((600 - spr.height) - 30 * push) if face else (598 - spr.height)
    img.paste(spr, (int(px - spr.width / 2), int(py + jolt * 0.6)), spr)

    # --- 鲸鳍一甩: a blue streak off her left fin, then a held afterimage
    if 188.70 <= t < 190.45:
        fu = clamp01((t - 188.70) / 0.85)
        fx = lerp(430, 58, ease(fu))
        fy = 452 + jolt * 0.6
        hold = 1.0 if t < 189.75 else clamp01(1.0 - (t - 189.75) / 0.66)
        for i in range(26):
            p = i / 25.0
            h = 34 * (0.30 + 0.70 * p)
            d.rectangle([fx + p * 250, fy - h / 2, fx + p * 250 + 7, fy + h / 2],
                        fill=kit.mix(BLUE_MID, 0.14 + 0.50 * (1 - p) * hold))
        # the fin itself, trailing the streak
        fw = 88
        d.polygon([(fx + 250, fy - 8), (fx + 250 + fw, fy - 26), (fx + 250 + fw * 0.86, fy + 4),
                   (fx + 250 + fw, fy + 26), (fx + 250, fy + 10)],
                  fill=kit.mix(BLUE_MID, 0.62 * hold))
        d.line([58, fy - 5, 250, fy - 5], fill=kit.mix(BLUE_TEXT, 0.5 * hold))
        d.line([58, fy + 5, 250, fy + 5], fill=kit.mix(BLUE_TEXT, 0.5 * hold))

    # --- spikes: a ring of noise shards pushed outward from her outline
    if face:
        gu = clamp01((t - 190.92) / 0.55)
        ex = gu if gu < 0.55 else clamp01((t - 191.22) / 1.30)
        r = random.Random(7)
        for i in range(72):
            ang = i * (2 * math.pi / 72) + r.uniform(-0.03, 0.03)
            ln = (70 + 190 * r.random()) * ex
            x0, y0 = 640, 330
            d.line([x0 + math.cos(ang) * 190, y0 + math.sin(ang) * 155,
                    x0 + math.cos(ang) * (190 + ln), y0 + math.sin(ang) * (155 + ln)],
                   fill=kit.mix(BLUE_TEXT, 0.20 + 0.45 * ex))

    # --- the three struck-through labels
    if t >= 191.60:
        for j in range(3):
            at = 191.60 + j * 0.34
            if t < at:
                continue
            au = clamp01((t - at) / 0.28)
            y = lerp(50, 168 + j * 44, ease(au))
            x = 300 - j * 40
            slab_text(d, (x, y), "大肥鱼", SZ_TITLE, kit.mix(BLUE_TEXT, 0.5 + 0.5 * au))
            if au > 0.6:
                d.line([x - 6, y + SZ_TITLE * 0.55, x + cjk_w("大肥鱼", SZ_TITLE) + 6,
                        y + SZ_TITLE * 0.55], fill=kit.mix(kit.ERR, 0.85))

    slab_text(d, (56, 664), "先别急着生气", SZ_BODY, kit.mix(STEEL, 0.9))
    caption(d, (W - 276, 668), "bridge 03/11", 14, 0.35)


# ================================================================ S44
def draw_s44(img, d, t, s):
    """81 你夸我一句 我尾音就糯回去  (195.64-202.96, 7.32 s)

    A puffed-up face crossfades into a soft one while the tail of the line is
    drawn as a descending dot curve ending in a glowing rice cake -- the sound
    made visible, and her single cutest frame."""
    u = s.u(t)
    d.line([0, 598, W, 598], fill=kit.mix(STEEL, 0.07))
    x0 = 240
    hard = sprite("exasperated", "bust", 470, 700)
    soft = smooth(clamp01((t - 195.95) / 1.30))
    py = 598 - hard.height
    img.paste(hard, (x0, py), hard)
    if soft > 0.01:
        gen = sprite("cheerful", "bust", 470, 700).resize(hard.size, Image.LANCZOS)
        gen.putalpha(gen.getchannel("A").point(lambda v: int(v * soft)))
        img.paste(gen, (x0, py), gen)

    lx, ly, lw, lh = 620, 210, 440, 200
    prog = clamp01((t - 195.95) / 2.60)
    last = None
    for i in range(34):
        p = i / 33.0
        if p > prog:
            break
        x, y = lx + p * lw, ly + (0.20 + 0.74 * p ** 1.7) * lh
        d.rectangle([x, y, x + 5, y + 5], fill=kit.mix(STEEL, 0.30 + 0.55 * p))
        if last is not None:
            d.line([last[0], last[1], x, y], fill=kit.mix(STEEL, 0.22 + 0.30 * p))
        last = (x + 2, y + 2)

    if prog > 0.36:
        nu = clamp01((t - 196.95) / 1.10)
        bounce = 14 * math.exp(-((t - 197.15) ** 2) / 0.02) if t > 196.9 else 0.0
        mochi(d, lx + lw, ly + lh * 0.94, 16 + 23 * nu + bounce, 1.0)
        cjk_text(d, (lx + lw - 92, ly + lh * 0.94 + 42), "尾音: 糯", SZ_BODY,
                 kit.mix(BLUE_TEXT, 0.92))

    caption(d, (lx, ly - 34), "tail_formant  f0 -12%", 15, 0.55)
    slab_text(d, (56, 664), "被夸就破功", SZ_BODY, kit.mix(STEEL, 0.9))
    caption(d, (W - 276, 668), "bridge 04/11", 14, 0.35)


# ================================================================ S45
def draw_s45(img, d, t, s):
    """82 你看 我就是这么没骨气  (202.96-205.86, 2.90 s)

    The rice cake deflates, she looks down, and a panel answers for her: 骨气 is
    a heat bar, and it drains to one cell while she watches."""
    u = s.u(t)
    d.line([0, 598, W, 598], fill=kit.mix(STEEL, 0.07))
    spr = sprite("shy", "bust", 430, 700)
    img.paste(spr, (300, 598 - spr.height), spr)

    if t < 203.62:
        nu = clamp01((t - 202.96) / 0.66)
        mochi(d, 900, 296, 44 * (1 - nu) + 5, 1 - nu)

    bx, by, bw, bh = 858, 372, 306, 152
    panel(d, (bx, by, bx + bw, by + bh), "gumption", 0.55, active=True, color=STEEL)
    cjk_text(d, (bx + 16, by + 14), "骨气", SZ_BODY, kit.mix(STEEL, 0.92))
    gv = 1.0 - 0.94 * smooth(clamp01((t - 203.20) / 1.65))
    for i in range(9):
        kit.heat_cell(d, bx + 22 + i * 30, by + 58, 24, 58, clamp01(gv * 1.06 - i * 0.01),
                      color=STEEL)
    cjk_text(d, (bx + 16, by + 122), "剩余 %d / 9" % int(round(gv * 9)), SZ_BODY,
             kit.mix(STEEL, 0.72))
    if gv < 0.22:
        caption(d, (bx + bw - 116, by + 16), "critically low", 14, 0.7)

    slab_text(d, (56, 664), "好吧 是我", SZ_BODY, kit.mix(STEEL, 0.9))
    caption(d, (W - 276, 668), "bridge 05/11", 14, 0.35)


# ================================================================ S46
def draw_s46(img, d, t, s):
    """83 好啦 我承认 我确实有点圆  (205.86-207.90, 2.04 s)

    Two seconds of nothing but a badly-round jello disc and one finger poking
    its edge so it wobbles. The admission is the whole frame."""
    u = s.u(t)
    cx, cy, R = 640, 312, 190
    _disc_soft(d, cx, cy, R, R * 0.90, t, 205.86)
    pu = clamp01((t - 206.55) / 0.75)
    if pu > 0:
        wob = math.exp(-6 * pu) * math.cos(30 * pu)
        d.rectangle([cx + R + 14 - 26 * pu, cy - 6, cx + R + 40 - 26 * pu, cy + 26],
                    fill=kit.mix(STEEL, 0.55))
        for i in range(3):     # the contact ring the poke puts into the surface
            rr = R * (0.90 + 0.10 * i * pu)
            d.arc([cx - rr, cy - R * 0.90 * (rr / R), cx + rr, cy + R * 0.90 * (rr / R)],
                  -46, 46, fill=kit.mix(STEEL, 0.34 * (1 - i * 0.22) * pu), width=2)
        for i in range(3):
            rr = 0.94 + 0.05 * i
            d.ellipse([cx - R * rr * (1 + 0.035 * wob), cy - R * 0.90 * rr * (1 + 0.030 * wob),
                       cx + R * rr * (1 + 0.035 * wob), cy + R * 0.90 * rr * (1 + 0.030 * wob)],
                      outline=kit.mix(STEEL, 0.28 - i * 0.06))
    caption(d, (cx - 76, cy + R + 46), "shape: round-ish", 15, 0.5)
    caption(d, (W - 276, 668), "bridge 06/11", 14, 0.35)


def _disc_soft(d, cx, cy, rx, ry, t, at):
    """The jelly disc. The rim is a band of small cells whose radius wobbles on a
    schedule keyed by index alone, so the shape is a pure function of t."""
    up = smooth(clamp01((t - at) / 0.70))
    rx *= 0.72 + 0.28 * up
    ry *= 0.72 + 0.28 * up
    n = 160
    for i in range(n):
        a = i * 2 * math.pi / n
        w = math.sin(i * 0.37) * 0.030 + math.sin(i * 1.09) * 0.016
        x, y = cx + math.cos(a) * rx * (1 + w), cy + math.sin(a) * ry * (1 + w)
        d.rectangle([x - 2, y - 2, x + 2, y + 2], fill=kit.mix(STEEL, 0.30))
    for r in range(5):
        rr = 1.0 - r * 0.15
        d.ellipse([cx - rx * rr, cy - ry * rr, cx + rx * rr, cy + ry * rr],
                  outline=kit.mix(STEEL, 0.09))


# ================================================================ S47
def draw_s47(img, d, t, s):
    """84 但圆怎么了 / 85 圆也是可爱的一种啊  (207.90-210.04, 2.14 s)

    The disc stops being a shape and starts being a face: it stretches sideways,
    its rim goes soft, and it sprouts a `:3`. Pushback turns into showing off."""
    u = s.u(t)
    cx, cy = 640, 312
    st = smooth(clamp01((t - 208.35) / 0.95))
    stretch = 1.0 + 0.45 * st
    ry = 176 * (1.0 - 0.10 * st)
    blob = smooth(clamp01((t - 208.35) / 1.10))

    n = 170
    for i in range(n):
        a = i * 2 * math.pi / n
        w = 1 + blob * (0.045 * math.sin(i * 0.23 + 1.1) + 0.030 * math.sin(i * 0.61))
        x, y = cx + math.cos(a) * 190 * stretch * w, cy + math.sin(a) * ry * w
        lv = 0.30 + 0.24 * blob * math.sin(i * 0.19)
        d.rectangle([x - 2, y - 2, x + 2, y + 2], fill=kit.mix(STEEL, clamp01(lv)))
    for r in range(4):
        rr = 1.0 - r * 0.17
        d.ellipse([cx - 190 * stretch * rr, cy - ry * rr, cx + 190 * stretch * rr, cy + ry * rr],
                  outline=kit.mix(BLUE_TEXT, 0.10 + 0.06 * r * blob))

    if t >= 208.60:
        eu = smooth(clamp01((t - 208.60) / 0.70))
        for sx in (-66, 62):
            kit.heat_cell(d, cx + sx - 10, cy - 62, 20, 20, 0.55 + 0.40 * eu, color=STEEL)
        for i in range(14):
            a = math.pi * (0.12 + 0.76 * (i / 13.0))
            x, y = cx + math.cos(a) * 42, cy + 24 - math.sin(a) * 22 * eu
            d.rectangle([x - 2, y - 2, x + 2, y + 2],
                        fill=kit.mix(BLUE_TEXT, (0.35 + 0.50 * eu) if i % 2 == 0 else 0.45 * eu))
    if t >= 209.10:
        hu = smooth(clamp01((t - 209.10) / 0.90))
        for r in range(5):
            k = 1.06 + 0.15 * r
            d.ellipse([cx - 190 * stretch * k, cy - ry * k,
                       cx + 190 * stretch * k, cy + ry * k],
                      outline=kit.mix(BLUE_MID, (0.34 - r * 0.055) * hu))
    if t < 208.30:
        slab_text(d, (56, 664), "但圆怎么了", SZ_BODY, kit.mix(STEEL, 0.92))
    else:
        slab_text(d, (56, 664), "圆也是可爱的一种啊", SZ_BODY, kit.mix(BLUE_TEXT, 0.95))
    caption(d, (W - 276, 668), "bridge 07/11", 14, 0.35)


# ================================================================ S48
def draw_s48(img, d, t, s):
    """86 我不是不需要人陪 / 87 我只是习惯了说不用  (210.04-214.28, 4.24 s)

    Back to the desk. The only prop is the chair nobody is sitting in: it lights
    up and comes forward, a hand holds it long enough for the dashes to go solid,
    then it leaves a mark in the dot field. The most naked beat of the song, so
    nothing else is allowed in."""
    u = s.u(t)
    desk(d, 150, 430, 1130, 612, 0.22)
    bowl(d, 470, 500, 62, 0.55, rice=True)
    bowl(d, 612, 522, 44, 0.30, rice=False)

    move = smooth(clamp01((t - 210.28) / 1.60))
    cx = lerp(920, 700, move)
    cw = lerp(180, 236, move)
    hold = smooth(clamp01((t - 212.10) / 0.55))
    press = 6 * math.exp(-6 * (t - 212.30)) if 212.30 <= t < 213.30 else 0.0
    cy = 452 + press
    gone = smooth(clamp01((t - 213.35) / 0.85))
    if 0.62 * (1 - gone) > 0.02:
        chair(d, cx, cy, cw, solid=hold * (1 - 0.2 * gone), level=0.62 * (1 - gone))

    if 212.10 <= t < 213.30:
        hu = clamp01((t - 212.10) / 0.30)
        hv = 1.0 if t < 212.85 else clamp01(1 - (t - 212.85) / 0.45)
        hand(d, cx + cw * 0.55, cy - cw * 0.30 - 34 + 26 * hu, 74, 46, hu * hv, -0.35, 0.62)

    if gone > 0.02:      # the dent: she sat there, and the field remembers
        for gy in range(int(cy - cw * 0.34), int(cy + cw * 0.34), 8):
            for gx in range(int(cx - cw * 0.42), int(cx + cw * 0.42), 8):
                if ((gx - cx) / (cw * 0.42)) ** 2 + ((gy - cy) / (cw * 0.34)) ** 2 > 1:
                    continue
                d.point((gx, gy), fill=kit.mix(STEEL, 0.16 * gone))

    caption(d, (168, 636), "table.cam  empty_chair = true", 15, 0.45)
    if t < 212.00:
        slab_text(d, (820, 664), "我不是不需要人陪", SZ_BODY, kit.mix(STEEL, 0.92))
    else:
        slab_text(d, (782, 664), "我只是习惯了说不用", SZ_BODY, kit.mix(BLUE_TEXT, 0.92))
    caption(d, (W - 276, 668), "bridge 08/11", 14, 0.35)


# ================================================================ S49
def draw_s49(img, d, t, s):
    """88 你要真喜欢 就直说嘛 / 89 我又不会笑你  (214.28-219.06, 4.78 s)

    The heartbeat cursor (M7) turns into a dialogue box nobody dares to type in.
    A hand nudges it forward, then pushes it across the desk and lets go: she
    hands the first move to the other person. The one blue thing is the cursor."""
    u = s.u(t)
    desk(d, 120, 400, 1160, 600, 0.20)
    bowl(d, 250, 336, 44, 0.26, rice=False)     # kept well clear of the sliding box

    push = smooth(clamp01((t - 215.30) / 0.60))
    slide = smooth(clamp01((t - 218.05) / 0.75))
    bx = 330 + 42 * push + 150 * slide
    by = 440 + 26 * push
    bw, bh = 520, 118
    panel(d, (bx, by, bx + bw, by + bh), "compose", 0.58, active=True, color=STEEL)
    d.line([bx + 18, by + 62, bx + bw - 18, by + 62], fill=kit.mix(STEEL, 0.35))
    d.line([bx + 18, by + 96, bx + bw - 18, by + 96], fill=kit.mix(STEEL, 0.22))

    hb = heartbeat(t)                                  # the film's 1.21 s pulse
    cx0 = bx + 22 + 62 * push
    d.rectangle([cx0, by + 40, cx0 + 13, by + 58], fill=kit.mix(BLUE_MID, 0.30 + 0.70 * hb))
    if hb > 0.05:
        d.rectangle([cx0 - 5, by + 36, cx0 + 18, by + 62], outline=kit.mix(BLUE_MID, 0.30 * hb))
    caption(d, (bx + bw - 132, by + 40), "0 chars", 15, 0.45)
    dec(d, (bx + 22, by + 70), "> say it.", 217.00, t, size=18, level=0.85, rate=9)

    if 215.55 <= t < 216.45:
        hu = clamp01((t - 215.55) / 0.28)
        hv = 1.0 if t < 216.05 else clamp01(1 - (t - 216.05) / 0.40)
        hand(d, bx + bw + 44, by + 104, 76, 46, hu * hv, -0.22, 0.60)
    if 218.05 <= t < 219.20:
        hu = clamp01((t - 218.05) / 0.30)
        hand(d, bx + bw + 40, by + 88, 72, 44, hu, -0.18, 0.55)
    if t >= 217.75:
        gu = smooth(clamp01((t - 217.75) / 0.80))
        slab_text(d, (W - 286, 366), "我不会笑你", SZ_MIN, kit.mix(STEEL, 0.42 + 0.34 * gu), pad=5)

    caption(d, (bx + 22, by + bh + 10), "cursor 1.21s = 2 beats", 14, 0.40)
    slab_text(d, (56, 664), "你先说", SZ_BODY, kit.mix(STEEL, 0.9))
    caption(d, (W - 276, 668), "bridge 09/11", 14, 0.35)


# ================================================================ S50
def draw_s50(img, d, t, s):
    """90 蓝鲸的骨架 撑得起一整片海  (219.06-222.90, 3.84 s)

    EXCEPTION BEAT: line 90 is not karaoke-captioned -- the whole sentence
    decodes out of noise in one pass, because it is the pivot of the act and the
    viewer has to read it as a complete thought.

    Visually the frame is "opened": the panel border walks off all four edges,
    the skeleton lines from S41 stretch out and become the sea, and the label at
    the bottom says what has just been proven."""
    u = s.u(t)
    grow = smooth(clamp01((t - 219.06) / 1.35))
    hw, hh = 400 + 240 * (1 - grow), 230 + 130 * (1 - grow)
    cx, cy = 640, 400
    for i in range(14):                                # deep water behind it all
        d.rectangle([cx - hw - 24, cy - hh + (2 * hh) * i / 14,
                     cx + hw + 24, cy - hh + (2 * hh) * (i + 1) / 14 + 1],
                    fill=kit.mix((4, 8, 34), 0.06 + 0.30 * (i / 13.0)))
    if hw > 3:
        panel(d, (cx - hw, cy - hh, cx + hw, cy + hh), "skeleton",
              0.62 * (1 - grow * 0.8), active=True, color=STEEL)

    water_bands(d, t, int(cy - hh * 0.85), int(cy + hh), bright=0.35 + 0.65 * grow,
                frozen=False)

    for j in range(7):                       # skeleton lines stretching sideways
        yy = cy - 96 + j * 32
        ex = ease(clamp01((t - 219.30 - j * 0.10) / 1.20))
        x0, x1 = cx - 240 * (1 - ex) - 40, cx + 240 * (1 - ex) + 40
        d.line([x0, yy, x1, yy], fill=kit.mix(BLUE_TEXT, 0.16 + 0.24 * ex))
        for k in range(9):
            d.point((x0 + (x1 - x0) * k / 8.0, yy), fill=kit.mix(STEEL, 0.35 * ex))

    if t >= 219.12:
        d.rectangle([180, 172, 1100, 310], fill=kit.BG)
    decode_cjk(img, "蓝鲸的骨架", 219.20, t, 640, 186, SZ_TITLE,
               kit.mix(STEEL, 0.97), 9.0, 41, glow=0.55)
    decode_cjk(img, "撑得起一整片海", 219.20, t, 640, 240, SZ_TITLE,
               kit.mix(BLUE_TEXT, 0.98), 9.0, 42, glow=0.65)

    if t >= 221.90:
        lu = smooth(clamp01((t - 221.90) / 0.85))
        caption(d, (56, 636), "SKELETON: LOAD-BEARING", 15, 0.30 + 0.45 * lu)
    caption(d, (W - 276, 668), "bridge 10/11", 14, 0.35)


# ================================================================ S51
def draw_s51(img, d, t, s):
    """91 别看我不动 我只是在等浪  (222.90-225.74, 2.84 s) -- BREATHING HOLE

    Total stillness. The waves keep the exact geometry they had at the end of
    S50 -- the geometry below is a function of the band index and nothing else --
    and only their shade breathes, slowly. The whale hangs suspended; the single
    brand-blue point is the heartbeat cursor at 1.21 s. On 等浪 it drops one cell
    and a dark swell starts in from the right and gets halfway, because the wave
    is not here yet. Nothing else moves: no flicker, no displacement, no cut."""
    u = s.u(t)
    for i in range(26):
        uu = i / 25.0
        y = int(120 + (708 - 120) * (uu ** 1.35))
        v = (0.10 + 0.30 * uu) * (0.55 + 0.45 * math.sin(i * 1.7 + 0.6)) * 0.95
        v *= 0.90 + 0.10 * pulse(t * 0.20 + i * 0.03, 8.0)     # brightness only
        d.rectangle([0, y, W, y + 3 + int(10 * uu)], fill=kit.mix(STEEL, clamp01(v) * 0.55))

    if t >= 224.30:                                # the swell, still on its way
        su = clamp01((t - 224.30) / 2.40)
        x0 = lerp(W + 60, 770, ease(su))
        for i in range(20):
            h = 90 + 40 * math.sin(i * 0.7)
            d.rectangle([x0 + i * 11, 250 - h / 2, x0 + i * 11 + 5, 250 + h / 2],
                        fill=kit.mix(STEEL, 0.10))
        d.line([x0, 0, x0 - 26, H], fill=kit.mix(STEEL, 0.16))

    sil = whale_sil(430, color=STEEL, rim=BLUE_MID, level=0.95)
    img.paste(sil, (int(640 - sil.width / 2), 300), sil)

    sink = 26 * smooth(clamp01((t - 224.20) / 1.10))
    hb = heartbeat(t, HEART)
    cx, cy = 640, 470 + sink
    r = 4 + 3.5 * hb
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=kit.mix(BLUE_MID, 0.55 + 0.45 * hb))
    d.ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5],
              outline=kit.mix(BLUE_MID, 0.30 * hb))

    slab_text(d, (56, 664), "安静 也是回答", SZ_BODY, kit.mix(STEEL, 0.86))
    caption(d, (W - 276, 668), "bridge 11/11", 14, 0.35)


SHOTS = {
    "S41": draw_s41,
    "S42": draw_s42,
    "S43": draw_s43,
    "S44": draw_s44,
    "S45": draw_s45,
    "S46": draw_s46,
    "S47": draw_s47,
    "S48": draw_s48,
    "S49": draw_s49,
    "S50": draw_s50,
    "S51": draw_s51,
}
