"""Shots S01-S16 -- Act I (0.00-43.76), Act II (43.76-60.94) and Act III open (60.94-86.04).

Everything here obeys the four conventions fixed by SHOTS.md section 4 and the
tuikit Chinese probe report:

  * brand blue (kit.BLUE_MID / kit.blue) is for HER only -- her body, rice, the
    heartbeat cursor, her name tag.  System things (cache, token counter, panel
    frames, fridges, weight columns) stay cold steel (STEEL / kit.amb).
  * at most ONE panel is active; every other panel is drawn with active=False
    (36% brightness).
  * Chinese never goes below 18 px; 14 px only for very short annotations.
  * `banner()` is Latin only, `panel()` titles are ASCII only, and Chinese that
    sits on a sprite / heat matrix gets an opaque slab behind it.

Layout note: pv.py paints the lyric band (a solid BG rect, y 620-704) on top of
everything a shot draws, so all content here stops at y = 612.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter

from pvlib.kit import *          # noqa: F401,F403  (W, H, kit, BLUE, STEEL, ...)
from pvlib import kit as K

# shotkit re-exports the easing helpers except these two, which still live in
# tuikit (kit.ease / kit.smooth).
ease = kit.ease
smooth = kit.smooth

# ------------------------------------------------------------------ constants

FLOOR = 612                 # nothing important is drawn below this line
HER_CX = 780                # the standing figure's x centre used across act 1
HER_TOP = 132               # bust 540x480 -> bottom lands exactly on FLOOR

_C: dict = {}


def cached(key, fn):
    """Tiny per-process memo; frames render in parallel chunks, in-process reuse."""
    v = _C.get(key)
    if v is None:
        v = _C[key] = fn()
    return v


# ------------------------------------------------------------------ helpers

def clear(img, d):
    d.rectangle([0, 0, W, H], fill=kit.BG)


def dotgrid(d, level, step=16, x0=0, y0=0, color=None):
    """The ambient dot field, redrawn at an arbitrary brightness."""
    if level <= 0.004:
        return
    c = kit.mix(color or STEEL, min(1.0, level))
    for y in range(y0, H, step):
        for x in range(x0, W, step):
            d.point((x, y), fill=c)


def blit(img, sp, x, y):
    img.paste(sp, (int(x), int(y)), sp)


def blit_c(img, sp, cx, cy):
    blit(img, sp, cx - sp.width / 2, cy - sp.height / 2)


def dotblock(d, x, y, size, color, filled=True):
    if filled:
        d.rectangle([x - size, y - size, x + size, y + size], fill=color)
    else:
        d.rectangle([x - size, y - size, x + size, y + size], outline=color)


def cjk_dec(d, xy, s, t, at, size, fill, rate=14.0, rngseed=0):
    """Typewriter + glyph flicker for Chinese (kit.decode is mono-only)."""
    if t < at:
        return
    rng = random.Random((hash((s, int(at * 1000))) ^ rngseed) & 0xFFFFFFFF)
    d.text(xy, kit.decode(s, t - at, rng, rate=rate), font=cjk(size), fill=fill)


def bar_glow(d, x0, y0, x1, y1, color, w=1):
    d.rectangle([x0, y0, x1, y1], outline=color, width=w)


def bezier(p0, p1, p2, p3, u):
    v = 1 - u
    x = v * v * v * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u * u * u * p3[0]
    y = v * v * v * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u * u * u * p3[1]
    return x, y


def her(expr="cheerful", mw=540, mh=520, tint="blue"):
    return cached(("sp", expr, mw, mh, tint),
                  lambda: sprite(expr, "bust", mw, mh, px=4, tint=tint))


def her_body(expr="cheerful", mw=230, mh=700, tint="blue"):
    """Whole figure (head to feet) so a shot can clip out her lower half."""
    return cached(("spb", expr, mw, mh, tint),
                  lambda: sprite(expr, "full", mw, mh, px=4, tint=tint))


def banner_c(text, rows, px=8, max_w=1180, level=0.9, fg=None):
    key = ("ban", text, rows, px, max_w, round(level, 2))
    return cached(key, lambda: banner(text, rows=rows, px=px,
                                      fg=fg or kit.mix(STEEL, level), max_w=max_w))


# ================================================================== S01
# dot field fades in from black, the giant banner builds D-E-E-P-S, gets eaten
# by noise, leaves a broken "DEEP S" whose glow twitches twice; bottom left a
# single decoded line: > 别叫我大肥鱼

def draw_s01(img, d, t, s):
    clear(img, d)
    dotgrid(d, 0.10 * clamp01(s.u(t) / 0.22))

    sp = banner_c("DEEPSEEK", rows=30, px=8, max_w=1000, level=0.92)
    bw, bh = sp.size
    bx, by = (W - bw) // 2, 178

    # build letters D E E P, then S stops 62% drawn
    reveal = 0.0
    for i in range(4):
        st = 0.55 + i * 0.46
        if t >= st:
            reveal = (i + clamp01((t - st) / 0.34)) / 8.0
    st = 2.39
    if t >= st:
        reveal = (4 + 0.62 * clamp01((t - st) / 0.30)) / 8.0
    if t >= 2.55:
        reveal = 4.62 / 8.0

    twitch = 0.0
    for at in (3.35, 4.02):
        if t >= at:
            twitch = max(twitch, math.exp(-7.0 * (t - at)))
    jit = int(3 * twitch * math.sin(t * 33.0))

    pw = max(1, int(bw * reveal))
    part = cached(("s01part", pw), lambda: sp.crop((0, 0, pw, bh)))
    glow = cached(("s01glow", pw), lambda: part.filter(ImageFilter.GaussianBlur(9)))

    blit(img, part, bx + jit, by)
    if twitch > 0.02:
        blit(img, kit.scale_alpha(glow, 0.55 * twitch), bx + jit, by)

    # the noise mouth: full block chewed out between 2.45 and 3.3
    a = 0.0
    if 2.42 <= t <= 3.30:
        a = clamp01((t - 2.42) / 0.30) * clamp01((3.30 - t) / 0.45)
    if a > 0.02:
        full = cached(("s01full",), lambda: banner_c("DEEPSEEK", rows=30, px=8,
                                                     max_w=1000, level=0.92))
        blit(img, full, bx, by)
        noise = cached(("s01n", bw, bh), lambda: kit.noise_tile(bw // 8, bh // 8, 8, "amber"))
        blit(img, kit.scale_alpha(noise, min(1.0, a * 1.25)), bx, by)

    # the decoded accusation, bottom left
    if t >= 1.30:
        cjk_dec(d, (78, 462), "> 别叫我大肥鱼", t, 1.30, SZ_BODY, kit.amb(1.0), rate=13.0)
        if t >= 1.30 + 8 / 13.0 - 0.05:
            k = pulse(t, 2 * HEART)
            if k > 0.45:
                d.rectangle([78 + cjk_w("> 别叫我大肥鱼", SZ_BODY) + 6, 486,
                             78 + cjk_w("> 别叫我大肥鱼", SZ_BODY) + 20, 496],
                            fill=kit.amb(0.9))

    caption(d, (80, 508), "name_check: rejected 1/1", 14, 0.42)


# ================================================================== S02
# she rises in at x=780, her hair colour is scanned on line by line; two field
# labels fill themselves in; at 10.86 the maid outfit drops as a grid and jams
# half way, 15 deg off; a checkbox hesitates.

def draw_s02(img, d, t, s):
    y = lerp(760, HER_TOP, ease(clamp01((t - 5.72) / 1.45)))
    x = HER_CX - 270
    st = her("cheerful", 540, 520, "amber")
    bl = her("cheerful", 540, 520, "blue")
    blit(img, st, x, y)

    scan = clamp01((t - 7.72) / 2.30)                     # line 4 starts 7.64
    if scan > 0:
        kit.paste_clipped(img, bl, int(x), int(y),
                          (int(x), int(y), int(x + 540), int(y + 480 * scan)))
        ly = y + 480 * scan
        if 0.0 < scan < 1.0:
            d.rectangle([x, ly - 2, x + 540, ly + 1], fill=kit.blue(0.95))
            d.rectangle([x, ly - 5, x + 540, ly + 4], outline=kit.blue(0.35))

    # terminal field labels
    for i, (lab, at) in enumerate((("hair: blue", 6.9), ("fin: side", 8.4))):
        if t >= at:
            dec(d, (150, 258 + i * 40), "> " + lab, t, at, size=18, level=0.85)
    caption(d, (150, 340), "assets/whale_maid.sprite", 13, 0.35)

    # maid outfit grid drops at 10.86 and jams 15 degrees off
    grid = cached(("s02grid",), _maid_grid)
    gr = cached(("s02grid15",), lambda: grid.rotate(15, resample=Image.BICUBIC,
                                                    expand=True, fillcolor=(0, 0, 0, 0)))
    gy = lerp(-340, 300, ease(clamp01((t - 10.86) / 1.05)))
    if t >= 10.86:
        blit(img, gr, HER_CX - gr.width / 2 + 18, gy)
        if t > 11.9:
            k = 0.5 + 0.5 * math.sin((t - 11.9) * 9.0)
            caption(d, (int(HER_CX - 60), int(gy + gr.height + 10)),
                    f"dress grid: jam {k:.1f}deg", 14, 0.55)
            d.rectangle([HER_CX - 40, gy + gr.height + 34, HER_CX - 40 + 120,
                         gy + gr.height + 36], fill=kit.amb(0.3))

    # hesitant checkbox
    if t >= 11.2:
        bx, by = 150, 452
        d.rectangle([bx, by, bx + 18, by + 18], outline=kit.amb(0.8))
        j = int(2 * math.sin((t - 11.2) * 7.0))
        cjk_text(d, (bx + 4 + j, by + 1), "?", 16, kit.anom(0.9))
        caption(d, (bx + 28, by + 2), "dress = true", 17, 0.85)
        caption(d, (bx, by + 26), "confirm? (y/n)", 14, 0.45)


def _maid_grid():
    cell, cols, rows, gap = 62, 5, 2, 6
    w = cols * (cell + gap)
    h = rows * (cell + gap)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    rng = random.Random(7)
    for r in range(rows):
        for c in range(cols):
            v = 0.18 + 0.55 * rng.random()
            x, y = c * (cell + gap), r * (cell + gap)
            im.paste(Image.new("RGBA", (cell, cell), kit.mix(STEEL, v) + (255,)), (x, y))
            dd.rectangle([x, y, x + cell - 2, y + cell - 2],
                         fill=kit.mix(STEEL, v) + (255,))
    return im


# ================================================================== S03
# data sea drifts sideways; a dotted fish swims right to left and, on "摸的是
# 自己", bends until it bites its own tail; then the whole thing closes into a
# ring and rolls around once and again.

def draw_s03(img, d, t, s):
    dx = -((t - 14.42) * 34.0) % W
    f = cached(("field",), field)
    img.paste(f, (int(dx), 0))
    img.paste(f, (int(dx) - W, 0))

    bite = clamp01((t - 16.30) / 0.95)
    spin = (t - 18.10) * 0.85 if t >= 18.10 else 0.0

    L = lerp(720, 1040, bite)
    R = L / (2 * math.pi)
    cx = lerp(lerp(1360, 460, ease(clamp01((t - 14.42) / 3.00))), 640, bite)
    cy = lerp(330, 330 - R, bite)
    A = bite * 2 * math.pi * 0.965
    pts = _spine(A, cx, cy, L, 46)

    if spin:
        ccx = sum(p[0] for p in pts) / len(pts)
        ccy = sum(p[1] for p in pts) / len(pts)
        pts = [(ccx + (px - ccx) * math.cos(spin) - (py - ccy) * math.sin(spin),
                ccy + (px - ccx) * math.sin(spin) + (py - ccy) * math.cos(spin))
               for px, py in pts]

    lv = 0.55 + 0.25 * bite
    n = len(pts)
    up, lo = [], []
    for i, (px, py) in enumerate(pts):
        i0, i1 = max(0, i - 1), min(n - 1, i + 1)
        tx, ty = pts[i1][0] - pts[i0][0], pts[i1][1] - pts[i0][1]
        tl = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / tl, tx / tl
        hh = 3 + 27 * _fish_w(i, n)
        up.append((px + nx * hh, py + ny * hh))
        lo.append((px - nx * hh, py - ny * hh))
    d.polygon(up + lo[::-1], fill=kit.blue(0.17 * lv / 0.55))
    for i, (px, py) in enumerate(pts[::2]):
        w = _fish_w(i * 2, n)
        dotblock(d, int(px), int(py), 2, kit.blue(lv * (0.55 + 0.45 * w)))

    # tail fin + the bitten tail joint
    tx, ty = pts[0]
    hx, hy = pts[-1]
    d.polygon([(tx, ty), (tx + 44, ty - 40), (tx + 26, ty), (tx + 44, ty + 40)],
              fill=kit.blue(0.22))
    d.line([tx, ty, tx + 40, ty - 34], fill=kit.blue(0.7), width=3)
    d.line([tx, ty, tx + 40, ty + 34], fill=kit.blue(0.7), width=3)
    if bite < 0.7:
        ex, ey = pts[-7]
        dotblock(d, int(ex), int(ey), 5, kit.BG)
        dotblock(d, int(ex), int(ey), 3, kit.blue(1.0))
        d.line([hx - 16, hy - 8, hx - 16, hy + 8], fill=kit.BG, width=3)
    if bite > 0.75:
        k = 0.45 + 0.55 * pulse(t, HEART)
        dotblock(d, int(tx), int(ty), 6, kit.blue(k), False)
        dotblock(d, int(hx), int(hy), 4, kit.blue(k))
    else:
        dotblock(d, int(hx), int(hy), 4, kit.blue(0.95))
        d.line([hx - 12, hy - 5, hx - 2, hy], fill=kit.blue(0.5), width=2)

    if spin:
        caption(d, (60, 120), "one more round: %.0f%%" % ((t - 18.10) * 13.5 % 100), 16, 0.5)
    elif t >= 14.42:
        caption(d, (60, 120), "data_sea :: drift", 16, 0.45)


def _spine(A, cx, cy, L, n):
    """Fish spine: a straight segment that bends into a closed ring as A -> 2pi."""
    if A < 0.06:
        return [(cx - L / 2 + L * i / (n - 1), cy) for i in range(n)]
    R = L / A
    ox, oy = cx, cy + R
    out = []
    for i in range(n):
        th = -A / 2 + A * i / (n - 1)
        out.append((ox + R * math.sin(th), oy - R * math.cos(th)))
    return out


def _fish_w(i, n):
    u = i / (n - 1)
    return math.sqrt(max(0.0, 1 - (2 * u - 1) ** 2)) ** 0.7


# ================================================================== S04
# a luminance tape (memory tape) scrolls past, seven small 大肥鱼 ride on it, a
# read head flashes each one red as it goes by; on the last line every fish but
# one goes dark and that one walks to the middle and holds perfectly still.

def draw_s04(img, d, t, s):
    tape = cached(("s04tape",), _memtape)
    off = int(-((t - 20.32) * 95.0) % W)
    y = 300
    blit(img, tape, off, y)
    blit(img, tape, off - W, y)
    blit(img, tape, off + W, y)

    head = 210
    d.line([head, y - 16, head, y + tape.height + 16], fill=kit.amb(0.8), width=2)
    caption(d, (head - 26, y - 38), "READ", 14, 0.6)

    chosen = 5
    for i in range(8):
        x = ((i * 178 + 40) - (t - 20.32) * 95.0) % (W + 360) - 180
        if t >= 23.42 and i == chosen:
            k = ease(clamp01((t - 23.42) / 1.10))
            slab_text(d, (lerp(x, W / 2 - 80, k), lerp(y + 26, 356, k)), "大肥鱼",
                      int(lerp(22, 40, k)), kit.amb(1.0), pad=5)
            continue
        lv = 0.85
        col = kit.amb(1.0)
        if abs(x - head) < 34:
            col = K.kit.ERR
        if t >= 23.42:
            lv = clamp01((23.42 + 1.0 - t) / 1.0)
        if lv > 0.06:
            slab_text(d, (x, y + 26), "大肥鱼", 22, kit.mix(col, 0.15 + 0.85 * lv), pad=4)

    if t >= 23.42:
        k = ease(clamp01((t - 23.42) / 1.10))
        d.rectangle([W / 2 - 112, 424, W / 2 + 112, 427],
                    fill=kit.mix(STEEL, 0.4 * (1 - k)))
    caption(d, (60, 470), "whale.memory[7]  ->  locked", 16, 0.5 if t < 23.42 else 0.75)


def _memtape():
    n = Image.effect_noise((320, 26), 85)
    n = n.point(lambda v: 255 if v > 205 else 0)
    return kit.scale_alpha(K.kit.tile_from_lum(n, 4, "amber"), 0.55)


# ================================================================== S05
# a concentric heat-cell disc reads "round"; a side panel checks shape and
# compares it with the whale skeleton.  The circle flashes red once, gets an X,
# and the skeleton turns blue.

def draw_s05(img, d, t, s):
    cx, cy = 372, 348
    flash = clamp01((t - 27.94) / 0.22) * clamp01((28.9 - t) / 0.5)
    for gy in range(110, 600, 14):
        for gx in range(120, 660, 14):
            r = math.hypot(gx - cx, gy - cy)
            band = min(abs(r - 44), abs(r - 92), abs(r - 140), abs(r - 188), abs(r - 232))
            if band > 7:
                continue
            v = 0.30 + 0.42 * (1 - r / 250.0) + 0.14 * math.sin(r * 0.19 - t * 2.3)
            col = K.kit.ERR if flash > 0.35 else STEEL
            K.kit.heat_cell(d, gx, gy, 12, 12, clamp01(v), col)
    if t >= 28.4:
        d.line([cx - 190, cy - 190, cx + 190, cy + 190], fill=K.kit.ERR, width=7)
        d.line([cx - 190, cy + 190, cx + 190, cy - 190], fill=K.kit.ERR, width=7)
    caption(d, (120, 96), "shape_check :: disc r=1.0", 15, 0.5)

    box = (720, 150, 1210, 470)
    panel(d, box, "shape_check", level=0.6, active=True)
    cjk_text(d, (752, 190), "体检报告", SZ_MIN, kit.amb(0.55))

    skel = t >= 27.94
    if skel:
        blit(img, cached(("s05skelb",), _skeleton), 752, 336)
    cjk_text(d, (752, 302), "鲸鱼骨架", SZ_MIN, kit.blue(0.95) if skel else kit.amb(0.35))

    caption(d, (752, 236), "[x] circle          0.00  rejected", 16, 0.85)
    caption(d, (752, 262), "[ ] whale_skeleton  --    accepted" if skel
            else "[ ] whale_skeleton  --    ...", 16, 0.85)
    if skel:
        cjk_text(d, (900, 302), "转蓝", SZ_MIN, kit.blue(0.9))
    d.line([752, 288, 1180, 288], fill=kit.amb(0.25))
    caption(d, (752, 430), f"verdict: not_fat   t={t:5.2f}s", 14, 0.5)


def _skeleton():
    """Her skeleton, drawn blue: the disc is the accusation, this is her answer."""
    im = Image.new("RGBA", (400, 40), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    for x in range(0, 400, 24):
        dd.line([x, 4, x, 36], fill=kit.mix(kit.BLUE_TEXT, 0.9) + (255,), width=3)
    dd.line([0, 20, 400, 20], fill=kit.mix(kit.BLUE_TEXT, 0.6) + (255,), width=2)
    return im


# ================================================================== S06
# a thin stream of rice runs along the bottom into a rice_bin panel whose
# counter climbs; the fridge on the right loses its lock icon and leaks blue.

def draw_s06(img, d, t, s):
    poke = 0.0
    if t >= 34.90:
        poke = math.exp(-6.0 * (t - 34.90)) * math.sin((t - 34.90) * 26.0)
    dy = int(8 * poke)

    # rice stream
    n = 34
    for i in range(n):
        p = (i / n + (t - 30.82) * 0.42) % 1.0
        x = lerp(250, 1245, p)
        y = 548 + dy + 16 * math.sin(p * 7.0 + (t - 30.82) * 1.6)
        col = kit.blue(0.45 + 0.5 * (1 - abs(0.5 - p) * 2))
        dotblock(d, int(x), int(y), 2, col)

    box = (80, 430 + dy, 330, 596 + dy)
    panel(d, box, "rice_bin", level=0.6, active=True)
    num = 1 + int((t - 30.82) * 13)
    d.text((104, 470 + dy), f"{num:04d}", font=mono_b(34), fill=kit.amb(0.95))
    caption(d, (104, 516 + dy), "rice/sec 13.0", 15, 0.6)
    K.bars(d, 104, 546 + dy, 200, 26, 16,
           [0.5 + 0.5 * math.sin(i * 1.3 + t * 4.0) for i in range(16)], color=STEEL)

    # fridge
    locked = t < 33.10
    bx0, by0, bx1, by1 = 930, 220 + dy, 1190, 560 + dy
    panel(d, (bx0, by0, bx1, by1), "fridge_unit", level=0.55, active=False)
    d.line([bx0 + 130, by0, bx0 + 130, by1], fill=kit.amb(0.4))
    d.line([bx0, by0 + 190, bx1, by0 + 190], fill=kit.amb(0.3))
    if locked:
        d.rectangle([bx0 + 150, by0 + 196, bx0 + 186, by0 + 226], outline=kit.amb(0.7))
        d.arc([bx0 + 158, by0 + 180, bx0 + 178, by0 + 206], 180, 360, fill=kit.amb(0.7), width=3)
        cjk_text(d, (bx0 + 156, by0 + 250), "锁", SZ_MIN, kit.anom(0.6))
    else:
        d.rectangle([bx0 + 130, by0 + 4, bx0 + 138, by1 - 4], fill=kit.blue(0.55))
        for k in range(7):
            d.rectangle([bx0 + 130, by0 + 30 + k * 70, bx0 + 260, by0 + 44 + k * 70],
                        outline=kit.blue(0.18))
        cjk_text(d, (bx0 + 150, by0 + 250), "门缝透光", SZ_MIN, kit.blue(0.8))

    cjk_text(d, (80, 386 + dy), "> 吃你点大米怎么了", 18, kit.amb(0.85))
    caption(d, (80, 410 + dy), f"stolen={num}g   no_lock={not locked}", 14, 0.45)


# ================================================================== S07
# the rice flows back into her hand as a bowl and chopsticks, a dotted chilli
# strip spins in and lands in it, then the frame wipes clean for the chorus.

def draw_s07(img, d, t, s):
    st = her("cheerful", 540, 520, "blue")
    blit(img, st, HER_CX - 270, HER_TOP)

    hand = (566, 400)
    # rice returning to her hand
    for i in range(26):
        p = (i / 26 + (t - 36.78) * 0.55) % 1.0
        a = clamp01((t - 36.78) / 1.2)
        sx = lerp(W + 80, hand[0], p)
        sy = lerp(120, hand[1], min(1.0, p * 1.25))
        dotblock(d, int(sx), int(sy), 2, kit.blue(0.35 + 0.55 * a))

    bowl = cached(("s07bowl",), lambda: K.kit.tile_from_lum(_bowl_lum(), 8, "amber"))
    land = ease(clamp01((t - 37.3) / 0.9))
    draw_bowl(d, hand[0] + 30, lerp(hand[1] - 70, 438, land))
    if land > 0.55:
        caption(d, (110, 430), "bowl + chopsticks: item acquired", 15, 0.55)

    # chilli strip: long red dotted band, flips in the air then drops in the bowl
    if t >= 39.0:
        k = clamp01((t - 39.0) / 1.9)
        x = lerp(W + 300, hand[0] - 20, ease(k))
        y = lerp(240, 372, ease(clamp01((k - 0.35) / 0.5)))
        ang = (t - 39.0) * 6.4
        h = max(4, int(30 * abs(math.cos(ang))))
        for i in range(30):
            px = int(x - 150 + i * 10)
            c = kit.mix(K.kit.ERR, 0.5 + 0.5 * math.sin(i * 0.7))
            d.rectangle([px, y - h // 2, px + 6, y + h // 2], fill=c)

    if t >= 41.3:
        cjk_text(d, (120, 470), "赔偿方案：自带碗筷 + 辣条", SZ_BODY, kit.amb(0.8))
    if t >= 36.78:
        caption(d, (120, 505), "> settle: bowl, chopsticks, chilli x1", 16, 0.6)

    wipe(img, (t - 42.46) / 1.30)


def _bowl_lum():
    im = Image.new("L", (34, 16), 0)
    dd = ImageDraw.Draw(im)
    dd.arc([1, 2, 33, 26], 0, 180, fill=255, width=2)
    dd.ellipse([3, 1, 31, 9], fill=190)
    dd.line([1, 6, 33, 6], fill=255)
    return im


def draw_bowl(d, cx, cy, k=1.0, body=None, rice=None):
    """A dotted rice bowl: rim, bowl body, a mound of rice, a pair of chopsticks.

    Every grain is drawn twice -- a BG halo first -- so the bowl stays readable
    when it lands on top of the sprite (same reason slab_text exists).
    """
    body = body or kit.mix(STEEL, 0.9)
    rice = rice or kit.blue(0.95)

    def grain(x, y, col, r=2):
        dotblock(d, int(x), int(y), r + 2, kit.BG)
        dotblock(d, int(x), int(y), r, col)

    for i in range(19):
        grain(cx + (i - 9) * 9 * k, cy, body)
    for i in range(31):
        a = math.pi * (0.06 + 0.88 * i / 30)
        grain(cx + 82 * k * math.cos(a), cy + 46 * k * math.sin(a), body)
    for i in range(23):
        a = math.pi * (0.05 + 0.9 * i / 22)
        grain(cx + 66 * k * math.cos(a), cy - 30 * k * math.sin(a), rice)
    for i in range(9):
        a = i * 2.1
        rr = 10 + i * 6
        grain(cx + rr * math.cos(a) * 0.8, cy - 14 - rr * math.sin(a) * 0.3, kit.blue(0.55), 1)
    d.line([cx - 60 * k, cy - 60 * k, cx + 46 * k, cy - 96 * k], fill=kit.BG, width=7)
    d.line([cx - 42 * k, cy - 60 * k, cx + 64 * k, cy - 96 * k], fill=kit.BG, width=7)
    d.line([cx - 60 * k, cy - 60 * k, cx + 46 * k, cy - 96 * k], fill=kit.amb(0.95), width=3)
    d.line([cx - 42 * k, cy - 60 * k, cx + 64 * k, cy - 96 * k], fill=kit.amb(0.8), width=3)


# ================================================================== S08
# LET ME GO and LET ME RUN ram each other, the impact blooms blue, 大肥鱼 lights
# up inside the glow and is struck through, then DEEPSEEK decodes underneath.

def draw_s08(img, d, t, s):
    clear(img, d)
    dotgrid(d, 0.10)

    hit = 44.82
    k = ease(clamp01((t - 43.86) / (hit - 43.86)))
    dim = 0.9 if t < hit + 0.25 else 0.9 * clamp01((hit + 1.25 - t) / 1.0) + 0.27

    lgo = banner_c("LET ME GO", rows=16, px=8, max_w=700, level=0.9)
    lru = banner_c("LET ME RUN", rows=16, px=8, max_w=700, level=0.9)
    lgo_d = banner_c("LET ME GO", rows=16, px=8, max_w=700, level=0.27)
    lru_d = banner_c("LET ME RUN", rows=16, px=8, max_w=700, level=0.27)
    lx = lerp(-lgo.width - 40, W / 2 - 14 - lgo.width, k)
    rx = lerp(W + 40, W / 2 + 14, k)
    y0 = 168

    # impact ring
    if t >= hit:
        e = (t - hit) / 0.85
        if e < 1.0:
            for i in range(110):
                a = i / 110 * 2 * math.pi
                r = e * 620
                x = W / 2 + r * math.cos(a)
                y = 330 + r * math.sin(a) * 0.52
                if 0 < x < W and 0 < y < H:
                    dotblock(d, int(x), int(y), 2, kit.blue((1 - e) * 0.85))
        sh = max(0.0, 1 - (t - hit) * 2.4)
        for i in range(26):
            off = (i - 13) * 46
            dotblock(d, int(W / 2 + off), 330, 2, kit.blue(0.35 * sh))

    blit(img, lgo if dim > 0.6 else lgo_d, lx, y0)
    blit(img, lru if dim > 0.6 else lru_d, rx, y0)

    # 大肥鱼 in the glow
    if t >= 45.00:
        g = ease(clamp01((t - 45.00) / 0.35))
        sz = int(lerp(44, 64, g))
        txt = "大肥鱼"
        ty = 336
        if t < 45.85:
            cjk_center(d, W / 2, ty, txt, sz, kit.amb(1.0))
        if t >= 45.85:
            strike = clamp01((t - 45.85) / 0.30)
            cjk_center(d, W / 2, ty, txt, sz, kit.amb(0.42))
            w = cjk_w(txt, sz)
            d.rectangle([W / 2 - w / 2 - 18, ty + sz * 0.48,
                         W / 2 - w / 2 - 18 + (w + 36) * strike,
                         ty + sz * 0.48 + 9], fill=kit.BG)
            d.rectangle([W / 2 - w / 2 - 18, ty + sz * 0.48,
                         W / 2 - w / 2 - 18 + (w + 36) * strike,
                         ty + sz * 0.48 + 9], outline=kit.amb(0.75))

    if t >= 46.35:
        dec(d, (W / 2 - 190, 470), "DEEPSEEK", t, 46.35, size=46, level=0.95, rate=9.0)
    if t < 45.0:
        caption(d, (60, 520), "chorus 1 :: collision", 16, 0.5)


# ================================================================== S09
# two whales cross the frame, the big one blows a string of letter bubbles.


def _s09_x(v: float) -> float:
    """Where the big whale is at song time `v` (used to anchor the bubbles)."""
    if v < 49.00:
        return lerp(-400, 700, ease(clamp01((v - 46.98) / 2.02)))
    return lerp(700, 1780, clamp01((v - 49.00) / 1.84) ** 1.6)


def draw_s09(img, d, t, s):
    # water: three drifting dotted layers
    for li, (base, amp, spd, step) in enumerate(((150, 12, 70, 30), (330, 18, 45, 26),
                                                 (540, 14, 58, 34))):
        ph = (t - 46.98) * spd
        for x in range(0, W + step, step):
            y = base + amp * math.sin((x + ph) / 150.0) + 16 * math.sin((x - ph * 1.7) / 60.0)
            dotblock(d, int(x), int(y), 1, kit.mix(STEEL, 0.16 + 0.10 * li))

    big = her("cheerful", 440, 440, "blue")
    small = her("starry", 240, 240, "blue")
    bx = _s09_x(t)
    by = 300 + 34 * math.sin((t - 46.98) * 2.60)
    blit_c(img, big, bx - 270, by + 74)
    blit_c(img, small, bx, by)

    # bubbles spelling BLUE WHALE; each one is anchored where it was blown out
    word = "BLUE WHALE"
    ci = 0
    for ch in word:
        if ch == " ":
            continue
        at = 48.20 + ci * 0.17
        ci += 1
        if t < at:
            continue
        life = t - at
        p = clamp01(life / 2.0)
        age = 1.0 if life < 1.7 else (1.0 if (life % 1.0) > 0.5 else 0.5)
        xx = _s09_x(at) + 70 + (ci - 1) * 58 + 16 * math.sin(life * 2.4 + ci)
        yy = by - 168 - p * 84
        s = 24
        d.rectangle([xx - s / 2, yy - s / 2, xx + s / 2, yy + s / 2],
                    outline=kit.blue(0.8))
        d.text((xx - 5, yy - 10), ch, font=mono_b(20), fill=kit.blue(age))
    if t >= 48.30:
        caption(d, (430, 470), "> blow(9)", 16, 0.55)

    if t >= 46.98:
        dec(d, (60, 540), "> swim(1)  swim(2)", t, 46.98, size=18, level=0.6, rate=16.0)


# ================================================================== S10
# night office, seen from above: desk, terminal, rice, a chair.  She walks in
# at 56.5, the screen wakes, and a 1.21 s cursor starts to breathe.  No words.


def draw_s10(img, d, t, s):
    arrive = clamp01((t - 56.5) / 1.6)
    awake = t >= 56.9

    # desk
    d.rectangle([300, 150, 980, 590], outline=kit.amb(0.30), width=2)
    d.rectangle([320, 170, 960, 570], outline=kit.amb(0.12))
    # a slow survey highlight
    sx = 320 + ((t - 50.84) * 55) % 640
    d.line([sx, 172, sx + 90, 172], fill=kit.amb(0.35))

    # chair
    d.rectangle([830, 380, 960, 520], outline=kit.amb(0.22))
    caption(d, (836, 528), "chair", 13, 0.3)

    # terminal
    d.rectangle([545, 215, 805, 345], outline=kit.amb(0.45), width=2)
    scr = (556, 226, 794, 334)
    lv = (0.10 + 0.06 * pulse(t)) * (2.0 if awake else 1.0)
    for yy in range(scr[1], scr[3], 10):
        for xx in range(scr[0], scr[2], 10):
            dr = 3 * math.sin((xx + yy) * 0.05 + (t - 50.84) * 0.7)
            dotblock(d, xx + int(dr), yy, 1, kit.mix(STEEL, min(1.0, lv)))
    if awake:
        k = heartbeat(t)
        d.rectangle([640, 268, 668, 274], fill=kit.blue(0.35 + 0.65 * k))
        d.rectangle([640, 282, 660, 288], fill=kit.mix(STEEL, 0.30))
    caption(d, (556, 348), "terminal :: screensaver" if not awake else "terminal :: idle",
            14, 0.5)

    # rice bowl, top view
    bcx, bcy = 430, 430
    for i in range(64):
        a = i / 64 * 2 * math.pi
        dotblock(d, int(bcx + 62 * math.cos(a)), int(bcy + 40 * math.sin(a)), 1, kit.amb(0.45))
    for i in range(26):
        a = i / 26 * 9.0 + 0.4
        rr = 6 + i * 1.9
        dotblock(d, int(bcx + rr * math.cos(a) * 0.9), int(bcy + rr * math.sin(a) * 0.55),
                 1, kit.blue(0.30 + 0.35 * abs(math.sin(i))))
    caption(d, (bcx - 44, bcy + 52), "rice", 13, 0.35)

    # she walks in and sits
    if arrive > 0:
        mw = int(lerp(240, 300, arrive) // 4 * 4)
        sp = her("cheerful", mw, mw + 40, "blue")
        cx = lerp(1330, 880, ease(arrive))
        cy = lerp(560, 430, ease(arrive))
        img.paste(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)), sp)
        dotgrid(d, 0.05 * arrive)

    caption(d, (60, 120), f"03:00 office / top view   t={t:5.2f}s", 15, 0.32)


# ================================================================== S11
# piano roll at the bottom, a clock panel up top, the rice bowl slides in, and
# the brass hit at 66.1 shakes the line and cuts her legs sideways.

def draw_s11(img, d, t, s):
    shake = 0.0
    if t >= 65.60:
        shake = math.exp(-4.0 * (t - 65.60)) * math.sin((t - 65.60) * 34.0)
    ox = int(6 * shake)

    def melody(u):
        v = 0.52 + 0.30 * math.sin(u * 15.0) + 0.14 * math.sin(u * 37.0 + 1.3)
        return clamp01(round(v * 11) / 11)

    col = K.kit.ERR if abs(shake) > 0.35 else kit.mix(STEEL, 0.8)
    K.kit.dot_chart(d, 70 + ox, 430, 1140, 170, melody, clamp01((t - 60.94) / 4.6),
                    col, sx=6, sy=6)

    box = (80, 130, 430, 300)
    panel(d, box, "00:03:00", level=0.6, active=True)
    d.text((104, 172), f"{int(t) // 60:02d}:{int(t) % 60:02d}:{int((t * 24) % 24):02d}",
           font=mono_b(34), fill=kit.amb(0.9))
    cjk_text(d, (104, 224), "钢琴还没停", SZ_MIN, kit.amb(0.6))
    K.bars(d, 104, 252, 280, 20, 18,
           [0.5 + 0.5 * math.sin(i * 0.9 + t * 5.2) for i in range(18)], color=STEEL)

    if t >= 63.48:
        k = ease(clamp01((t - 63.48) / 1.3))
        bx = lerp(1420, 980, k) + ox
        by = lerp(700, 466, k)
        draw_bowl(d, bx, by, 0.9)
        cjk_text(d, (bx - 34, by + 62), "白饭", SZ_MIN, kit.blue(0.85))

    # legs answering the brass
    if t >= 65.20:
        swing = math.sin((t - 65.20) * 4.4)
        sp = her_body("cheerful", 200, 620)
        kit.paste_clipped(img, sp, int(1090 + swing * 18 + ox), 240,
                          (1040, 498, 1275, FLOOR))
        caption(d, (836, 560), "legs: out of control", 15, 0.7)

    caption(d, (70, 396), "piano_roll / bar 1-4", 15, 0.5)


# ================================================================== S12
# rice flies out of the bowl into a heat-cell column: one bowl writes all day.
# The brass reaction from line 23 is still running through the first second.

def draw_s12(img, d, t, s):
    col = (150, 170, 270, 596)
    lvl = clamp01((t - 66.4) / 3.2) * 0.66
    _column(d, col, lvl, STEEL)
    d.text((150, 118), f"{lvl * 1.5:.2f} DAY", font=mono_b(30), fill=kit.amb(0.9))
    cjk_text(d, (150, 620 - 40), "能量柱", SZ_MIN, kit.amb(0.6))

    # brass afterglow + legs, line 23 is sung 66.12-68.46
    if t < 68.6:
        k = clamp01((68.6 - t) / 2.0)
        swing = math.sin((t - 66.12) * 4.6) * k
        sp = her_body("cheerful", 200, 620)
        kit.paste_clipped(img, sp, int(1090 + swing * 20), 240, (1040, 498, 1275, FLOOR))
        caption(d, (836, 560), "brass hit -> legs", 15, 0.6 * k + 0.2)
        for i in range(14):
            yy = 300 + i * 14
            d.line([700, yy, 700 + int(60 * k * abs(math.sin(i + t * 6))), yy],
                   fill=kit.anom(0.5 * k))

    # rice stream from the bowl into the column
    for i in range(30):
        p = (i / 30 + (t - 66.12) * 0.5) % 1.0
        x, y = bezier((1030, 470), (760, 540), (420, 250), (240, 190), p)
        dotblock(d, int(x), int(y), 2, kit.blue(0.35 + 0.5 * (1 - p)))

    cjk_text(d, (300, 560), "白饭是我的燃料", SZ_BODY, kit.blue(0.9))
    caption(d, (300, 596), "fuel: rice", 18, 0.85)
    caption(d, (560, 118), f"charge {lvl:4.2f} / 1.00", 16, 0.6)


def _column(d, box, level, color, cells=20, gap=2):
    x0, y0, x1, y1 = box
    n = int((y1 - y0) // (cells + gap))
    for i in range(n):
        y = y1 - (i + 1) * (cells + gap)
        for j in range(int((x1 - x0) // (cells + gap))):
            x = x0 + j * (cells + gap)
            on = (i + 0.5) / n <= level
            v = 0.55 + 0.35 * math.sin(i * 0.8 - (level * 9.0))
            K.kit.heat_cell(d, x, y, cells, cells, v if on else 0.04, color)
    d.rectangle(box, outline=kit.mix(color, 0.5))
    return level


# ================================================================== S13
# the counter rolls 1 DAY -> 1 YEAR and overflows (top cell red), then a second
# column marked WORK shows up and stops dead at 30%.

def draw_s13(img, d, t, s):
    colA = (150, 170, 270, 596)
    lvlA = lerp(0.66, 1.0, ease(clamp01((t - 70.90) / 1.30)))
    _column(d, colA, lvlA, STEEL)
    over = t > 73.30
    d.text((150, 118), "1 YEAR" if t > 73.2 else "1 DAY", font=mono_b(30),
           fill=K.kit.ERR if over else kit.amb(0.9))
    if over:
        k = heartbeat(t, 0.5)
        K.kit.heat_cell(d, 150, 170 - 26, 120, 22, 0.7 + 0.3 * k, K.kit.ERR)
        caption(d, (150, 96), "counter overflow", 15, 0.9)

    colB = (700, 170, 820, 596)
    if t >= 74.10:
        lvlB = clamp01((t - 74.10) / 1.00) * 0.30
        _column(d, colB, lvlB, STEEL)
        d.text((700, 118), "WORK", font=mono_b(30), fill=kit.amb(0.85))
        d.text((700, 600), f"{lvlB * 100:4.1f}%", font=mono_b(18), fill=kit.amb(0.7))
        cjk_text(d, (860, 380), "两碗能写到明年", SZ_BODY, kit.amb(0.75))
        if t > 75.1:
            caption(d, (860, 418), "and then it stops.", 16, 0.6)


# ================================================================== S14
# the WORK column slumps; inference_effort shows four gears with only `low`
# lit, and `saving power...` types itself out.

def draw_s14(img, d, t, s):
    colB = (700, 170, 820, 596)
    drop = 0.0
    if t >= 75.94:
        drop = 10 * clamp01((t - 75.94) / 0.35)
        if t > 76.4:
            drop += 3 * math.exp(-6 * (t - 76.4)) * math.sin((t - 76.4) * 30.0)
    _column(d, (colB[0], colB[1] + drop, colB[2], colB[3]), 0.30, STEEL)
    if 75.44 <= t < 76.6:
        k = clamp01((75.9 - t) / 0.45)
        K.kit.heat_cell(d, colB[0], colB[1] - 26 + drop, 120, 22, 0.4 + 0.6 * k, K.kit.ERR)

    box = (120, 330, 700, 596)
    panel(d, box, "inference_effort", level=0.6, active=True)
    cjk_text(d, (146, 366), "推理强度", SZ_MIN, kit.amb(0.6))
    names = ("low", "mid", "high", "max")
    for i, nm in enumerate(names):
        x = 146 + i * 132
        y = 402
        if i == 0:
            d.rectangle([x, y, x + 116, y + 58], fill=kit.mix(STEEL, 0.30),
                        outline=kit.amb(0.9), width=2)
            d.text((x + 34, y + 18), nm, font=mono_b(22), fill=kit.amb(1.0))
        else:
            for gx in range(x, x + 116, 8):
                d.line([gx, y, gx, y + 58], fill=kit.mix(STEEL, 0.10))
            d.rectangle([x, y, x + 116, y + 58], outline=kit.amb(0.22))
            d.text((x + 30, y + 18), nm, font=mono_b(22), fill=kit.amb(0.28))
    if t >= 76.5:
        dec(d, (146, 490), "> saving power...", t, 76.5, size=20, level=0.85, rate=13.0)
    cjk_text(d, (146, 530), "不是我不想干活", SZ_BODY, kit.amb(0.8))
    caption(d, (146, 566), f"effort=low   draw={0.30:4.2f}", 15, 0.5)


# ================================================================== S15
# the saved wattage leaves the `low` gear as a blue thread, crosses the whole
# frame and lands in a big panel called for_you, where something starts to beat.

def draw_s15(img, d, t, s):
    # the effort panel stays, dimmed
    box = (120, 330, 700, 596)
    panel(d, box, "inference_effort", level=0.6, active=False)
    x, y = 146, 402
    d.rectangle([x, y, x + 116, y + 58], fill=kit.mix(STEEL, 0.22), outline=kit.amb(0.4))
    d.text((x + 34, y + 18), "low", font=mono_b(22), fill=kit.amb(0.55))

    for_you = (760, 170, 1210, 560)
    panel(d, for_you, "for_you", level=0.7, active=True)

    p0, p1, p2, p3 = (250, 430), (520, 120), (760, 600), (985, 365)
    fly = clamp01((t - 79.00) / 2.10)
    for i in range(22):
        u = fly - i * 0.017
        if u <= 0:
            continue
        px, py = bezier(p0, p1, p2, p3, u)
        a = (1 - i / 22.0) ** 1.3 * clamp01(fly * 3)
        dotblock(d, int(px), int(py), 4 if i == 0 else 3, kit.blue(0.35 + 0.65 * a))
    if 0 < fly < 1:
        hx, hy = bezier(p0, p1, p2, p3, fly)
        for r in (14, 22):
            dotblock(d, int(hx), int(hy), r // 2, kit.blue(0.30), False)

    if fly >= 0.999:
        k = 0.5 + 0.5 * math.sin(2 * math.pi * (t - 81.1) / HEART)
        for i in range(5):
            r = 40 + i * 34 + 10 * k
            d.rectangle([985 - r, 365 - r * 0.62, 985 + r, 365 + r * 0.62],
                        outline=kit.blue((0.5 - i * 0.08) * (0.5 + 0.5 * k)))
        d.rectangle([985 - 14 - 6 * k, 365 - 14 - 6 * k, 985 + 14 + 6 * k, 365 + 14 + 6 * k],
                    fill=kit.blue(0.35 + 0.6 * k))
        caption(d, (790, 520), "output: for you", 16, 0.7)

    cjk_text(d, (146, 566), "省下来的那点电", SZ_BODY, kit.amb(0.8))
    cjk_text(d, (790, 576), "全用来想你了", SZ_BODY, kit.blue(0.9 if fly >= 1.0 else 0.5))
    caption(d, (60, 120), f"power_route  {(fly * 100):5.1f}%", 15, 0.5)

    wipe(img, (t - 82.06) / 0.80)


# ================================================================== S16
# half a second of black, then LET ME GO, LET ME RUN slams out of the middle,
# jittering under a noise field, and a DEEPSEEK line flashes at the tail.

def draw_s16(img, d, t, s):
    clear(img, d)
    v = (t - 82.86)
    if v < 0.50:
        return
    dotgrid(d, 0.10 * clamp01((v - 0.50) / 0.35))

    sp = banner_c("LET ME GO, LET ME RUN", rows=18, px=8, max_w=1160, level=0.95)
    k = clamp01((v - 0.50) / 1.05)
    sc = lerp(0.22, 1.14, ease(k))
    if k >= 1:
        sc = 1.14 + 0.02 * math.exp(-8 * (v - 1.55)) * math.sin((v - 1.55) * 40)
    w = max(2, int(sp.width * sc))
    h = max(2, int(sp.height * sc))
    big = cached(("s16big", w, h), lambda: sp.resize((w, h), Image.NEAREST))
    jx = int(3 * math.sin(v * 41.0) * clamp01((1.8 - v) / 1.0))
    blit_c(img, big, W / 2 + jx, 316)

    # corner bloom
    if k > 0.05:
        for (cx0, cy0) in ((70, 70), (W - 70, 70), (70, H - 90), (W - 70, H - 90)):
            for i in range(16):
                a = i / 16 * 2 * math.pi
                rr = 26 + i * 2 + 8 * math.sin(v * 6 + i)
                dotblock(d, int(cx0 + rr * math.cos(a)), int(cy0 + rr * math.sin(a) * 0.7),
                         2, kit.blue(0.5 * k * (1 - i / 16.0)))

    noise = cached(("s16n", int(v * 12) % 6), lambda: kit.noise_tile(140, 22, 8, "amber"))
    blit(img, kit.scale_alpha(noise, 0.22 * clamp01(k)),
         int(W / 2 - big.width / 2), int(316 - big.height / 2))

    if v >= 2.45:
        f = 0.5 + 0.5 * math.sin((v - 2.45) * 14.0)
        txt = "DEEPSEEK"
        d.text((W / 2 - mono_b(44).getlength(txt) / 2, 505), txt,
               font=mono_b(44), fill=kit.amb(0.35 + 0.65 * f))
    caption(d, (60, 120), "chorus 2 :: run", 16, 0.45)


# ================================================================== registry

SHOTS = {
    "S01": draw_s01, "S02": draw_s02, "S03": draw_s03, "S04": draw_s04,
    "S05": draw_s05, "S06": draw_s06, "S07": draw_s07, "S08": draw_s08,
    "S09": draw_s09, "S10": draw_s10, "S11": draw_s11, "S12": draw_s12,
    "S13": draw_s13, "S14": draw_s14, "S15": draw_s15, "S16": draw_s16,
}
