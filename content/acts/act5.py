"""Group 5 -- S52..S57, the third chorus and the outro (225.74 - 268.40 s).

This group closes the film. Two things are load-bearing.

Chorus 3 (S52-S54) has to read as the *same* chorus and as the *third* one at a
glance. SHOTS.md 4.3 puts that difference in four places and this file does all
four: the banner breaks out of the water instead of standing still or scrolling,
the banner is smaller with softer light than either earlier pass (60% against
100% / 70%), the theme line is rewritten ("明天再摸鱼 今天就到这") and gets the
film's only whole-sentence glow, and the closing shot is shorter and darker than
its two predecessors (7.15 s, picture stepped down to 30%).

S57 has to end in real black. Its last breath is the M7 heartbeat cursor -- the
same #4D6BFE block that has been breathing at 1.21 s since S10 -- and once it has
blinked three times there is nothing left on the canvas at all.

Brand blue is spent only on her: the heartbeat cursor, the water she breaks, the
soft light around the nickname, the whale that swims past. System furniture stays
cold steel.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from pvlib.kit import *  # noqa: F401,F403  (the shared interface, by contract)

# ------------------------------------------------------------------ constants

WATER = 430.0                       # the surface the S52 banner comes up through
THEME = "明天再摸鱼 今天就到这"      # the third pass rewrites the theme line
FISH = "大肥鱼"
ROMAN = "MDCLXVI"                   # deterministic flicker for decode/erase

# 100% -> 70% -> 60%: the banner shrinks and the light gets softer every pass.
BANNER_ROWS, BANNER_PX = 13, 6      # ~660x78, i.e. 60% of the 1085 px first pass


# ------------------------------------------------------------------ helpers

_NOISE: dict = {}


def _noise(seed: int, w: int, h: int) -> Image.Image:
    """Deterministic noise. PIL's effect_noise is entropy-seeded, and a shot has
    to be a pure function of t -- two frames of the same t must be identical.
    """
    key = (seed, w, h)
    if key not in _NOISE:
        rng = random.Random((seed * 2654435761) & 0xFFFFFFFF)
        im = Image.new("L", (w, h))
        im.putdata([rng.randrange(256) for _ in range(w * h)])
        _NOISE[key] = im
    return _NOISE[key]


def _put(img: Image.Image, im, xy) -> None:
    if im is not None and xy is not None:
        img.paste(im, xy, im)


def _shaped(mask: Image.Image, px: int, tint: str = "amber") -> Image.Image:
    """A luminance mask as square ink, one cell per px*px square."""
    return kit.tile_from_lum(mask, px, tint)


def _text_img(txt: str, size: int, fill, pad: int = 24) -> Image.Image:
    """A Chinese word as a transparent layer, offset by (12, 8) from its box."""
    im = Image.new("RGBA", (int(cjk_w(txt, size)) + pad, size + 32), (0, 0, 0, 0))
    cjk_text(ImageDraw.Draw(im), (pad // 2, 8), txt, size, fill)
    return im


def _glow(txt: str, size: int, level: float) -> Image.Image:
    """A soft halo behind a Chinese word -- the light the nickname finally gets."""
    w = int(cjk_w(txt, size)) + 64
    im = Image.new("RGBA", (w, size + 64), (0, 0, 0, 0))
    cjk_text(ImageDraw.Draw(im), (32, 32), txt, size, kit.mix(kit.BLUE_TEXT, level))
    return im.filter(ImageFilter.GaussianBlur(size * 0.30))


def _rng(tag: int) -> random.Random:
    return random.Random(hash((tag, 0x5A17)) & 0xFFFFFFFF)


_DISSOLVE: dict = {}


def _dissolve(a: float, floor: float = WATER) -> Image.Image:
    """Screen-space static, cached per alpha step: the water eating itself away.

    It is masked to the region below `floor` with a 90 px ramp, because the
    still surface is what disappears here -- a dissolve over the whole frame
    just looks like snow.
    """
    if a <= 0.01:
        return None
    k = round(min(1.0, a), 3)
    if k not in _DISSOLVE:
        rng = _rng(52)
        bits = _noise(52, W // 16 + 4, H // 16 + 4).point(
            lambda v: 255 if v > rng.randrange(40, 216) else 0)
        tile = kit.tile_from_lum(bits, 16, "blue")
        top = max(0.0, floor - 90.0)
        span = max(1.0, H - top)
        grad = Image.new("L", (1, H))
        grad.putdata([int(255 * clamp01((y - top) / span) ** 1.4) for y in range(H)])
        grad = grad.resize((W, H))
        a_ch = ImageChops.multiply(tile.getchannel("A"), grad.crop((0, 0, tile.width, tile.height)))
        tile.putalpha(a_ch.point(lambda v: int(v * k * 0.85)))
        _DISSOLVE[k] = tile
    return _DISSOLVE[k]


_DIM: dict = {}


def _dim_layer(v: float) -> Image.Image:
    """A darkness veil whose density grows from the centre outwards."""
    if v <= 0:
        return None
    k = round(clamp01(v), 3)
    if k not in _DIM:
        sm = Image.new("L", (64, 36), 0)
        px = sm.load()
        for y in range(36):
            for x in range(64):
                dx, dy = (x - 31.5) / 32.0, (y - 17.5) / 18.0
                px[x, y] = int(255 * clamp01(k * (0.68 + 1.40 * min(1.0, math.hypot(dx, dy)))))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lay.putalpha(sm.resize((W, H), Image.BILINEAR))
        _DIM[k] = lay
    return _DIM[k]


def _eclipse(img: Image.Image, fx: float, fy: float, a: float) -> None:
    """Real black covering a fraction of the frame along each axis.

    `fx`/`fy` are how much of the width/height is already dark, so (0, 1) wipes
    left to right and (1, 0) wipes top to bottom. Used for the clear sweep into
    S55 and for the final blackout.
    """
    a = clamp01(a)
    fx, fy = clamp01(fx), clamp01(fy)
    if a <= 0 or (fx <= 0 and fy <= 0):
        return
    nx, ny = 80, 48
    small = Image.new("L", (nx, ny), 0)
    px = small.load()
    for yy in range(ny):
        for xx in range(nx):
            if xx / float(nx - 1) < fx or yy / float(ny - 1) < fy:
                px[xx, yy] = 255
    if a < 0.999:
        small = small.point(lambda v: int(v * a))
    img.paste(Image.new("RGB", (W, H), kit.BG), (0, 0), small.resize((W, H), Image.BILINEAR))


_BAND: dict = {}


def _band(x0: float, y0: float, x1: float, y1: float, v: float, rings: int = 10) -> Image.Image:
    """A slab that fades into the picture instead of cutting a hard rectangle.

    Drawn as a few nested rectangles of falling alpha: the centre is solid enough
    to lift Chinese off her uniform, the edge dissolves into the collage.
    """
    key = (int(x0), int(y0), int(x1), int(y1), round(v, 3), rings)
    if key not in _BAND:
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        for i in range(rings):
            k = i / float(max(1, rings - 1))                 # 0 at the rim, 1 at the core
            inset = 12.0 * (1.0 - k)
            dd.rectangle([x0 + inset, y0 + inset, x1 - inset, y1 - inset],
                         fill=kit.BG + (int(255 * v * (0.30 + 0.70 * k) / rings * 2.6),))
        _BAND[key] = im
    return _BAND[key]


_SPARK: dict = {}


def _sparkle(k: int) -> Image.Image:
    if k not in _SPARK:
        _SPARK[k] = kit.noise_tile(k, k, 1, "blue")
    return _SPARK[k]


_CROSS: dict = {}


def _cross(k: int) -> Image.Image:
    if k not in _CROSS:
        m = Image.new("L", (k, k), 0)
        dd = ImageDraw.Draw(m)
        c = k // 2
        dd.line([c, 0, c, k - 1], fill=255)
        dd.line([0, c, k - 1, c], fill=255)
        _CROSS[k] = kit.tile_from_lum(m, 1, "blue")
    return _CROSS[k]


_WHALE: dict = {}


def _whale(w: int, h: int, lv: float, tint: str = "blue") -> Image.Image:
    """Her other shape as a clean silhouette: a body, a fluke, a fin, a lit eye.

    Lifted from the standing sprite it reads as a smudge, so the outline is
    drawn directly -- it has to survive being shrunk to a third of the frame.
    """
    if (w, h) not in _WHALE:
        m = Image.new("L", (w, h), 0)
        dd = ImageDraw.Draw(m)
        bw, bh = int(w * 0.78), int(h * 0.62)
        bx, by = 0, int(h * 0.24)
        dd.ellipse([bx, by, bx + bw, by + bh], fill=255)          # body
        dd.polygon([(bx + bw - 10, by + bh // 2), (w - 2, 2), (w - 2, h - 2)], fill=255)
        dd.polygon([(bx + int(bw * 0.30), by + bh - 6),
                    (bx + int(bw * 0.16), h - 2),
                    (bx + int(bw * 0.50), by + bh - 14)], fill=255)   # pectoral fin
        dd.ellipse([bx + int(bw * 0.16), by + int(bh * 0.42),
                    bx + int(bw * 0.26), by + int(bh * 0.58)], fill=0)
        _WHALE[(w, h)] = m
    im = kit.tile_from_lum(_WHALE[(w, h)], 3, tint)
    return kit.scale_alpha(im, lv)


# --------------------------------------------------------------- set pieces

def _drops(img: Image.Image, cx: float, cy: float, at: float, t: float, life: float = 1.25) -> None:
    """A splash: grains thrown up from (cx, cy), falling back under gravity."""
    age = t - at
    if age <= 0 or age >= life:
        return
    sp = _sparkle(34)
    half = 17
    for i in range(48):
        f = (i * 0.6180339887) % 1.0
        a = -2.74 + 1.18 * f
        spd = 58 + ((i * 29) % 7) * 18
        p = 1.0 - age / life
        x = cx + math.cos(a) * spd * age
        y = cy + math.sin(a) * spd * age + 360 * age * age
        if not (-40 < x < W + 40 and -40 < y < H + 40):
            continue
        fade = int(255 * p ** 1.5)
        if fade < 8:
            continue
        col = kit.mix(kit.BLUE_TEXT, 0.50 + 0.50 * f, kit.BG)
        a_ch = sp.getchannel("A")
        a_ch.putdata([fade] * (34 * 34))
        part = ImageOps.colorize(a_ch, black=kit.BG, white=col).convert("RGBA")
        part.putalpha(a_ch)
        img.paste(part, (int(x) - half, int(y) - half), part)


def _water(d: ImageDraw.ImageDraw, t: float, y: float = WATER) -> None:
    """The still surface of S51, one second before it is broken."""
    d.rectangle([0, y, W, H], fill=kit.mix(kit.BLUE_LO, 0.42, kit.BG))
    for i in range(10):
        yy = y + 10 + i * 11
        if yy > H:
            break
        for x in range(0, W, 5):
            h = math.sin(x * 0.014 + t * (1.5 + 0.20 * i) + i * 0.8) * (2.4 + 0.45 * i)
            d.point((x, yy + h), fill=kit.mix(kit.BLUE_TEXT, max(0.0, 0.26 - 0.022 * i)))
    d.line([0, y, W, y], fill=kit.mix(kit.BLUE_TEXT, 0.72))
    d.line([0, y + 2, W, y + 2], fill=kit.mix(kit.BLUE_TEXT, 0.20))


def _counter(d: ImageDraw.ImageDraw, t: float, glow: float) -> None:
    """The S06 white-rice meter, back for one line as a callback.

    Top-left, clear of her head: the whole point is that the number is the same.
    """
    x0, y0, x1, y1 = 58, 54, 372, 200
    panel(d, (x0, y0, x1, y1), "rice: stolen", level=0.62, active=True)
    caption(d, (x0 + 14, y0 + 18), "count", 14, 0.45)
    d.text((x0 + 14, y0 + 34), "1024", font=mono_b(30),
           fill=kit.mix(kit.BLUE_TEXT, 0.45 + 0.45 * glow))
    caption(d, (x0 + 158, y0 + 52), "grains", 13, 0.40)
    bars(d, x0 + 14, y0 + 84, x1 - x0 - 28, 22, 16,
         [0.5 + 0.5 * math.sin(t * 2.3 + k * 0.6) for k in range(16)], 2, kit.UI)
    caption(d, (x0 + 14, y0 + 114), "> shipped as fuel", 13, 0.30 + 0.22 * glow)


def _nametag(t: float, lv: float = 1.0) -> Image.Image:
    """The small plate the nickname finally gets filed into (S53)."""
    x0, y0, x1, y1 = 940, 470, 1248, 612
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    panel(d, (x0, y0, x1, y1), "name tag", level=0.58, active=True)
    cjk_text(d, (x0 + 26, y0 + 28), FISH, 32, kit.mix(kit.UI, 0.94))
    caption(d, (x0 + 26, y0 + 84), "aka", 13, 0.35)
    d.text((x0 + 64, y0 + 78), "DEEPSEEK", font=mono(19),
           fill=kit.mix(kit.BLUE_TEXT, 0.50 + 0.40 * pulse(t, HEART)))
    return kit.scale_alpha(im, lv)


def _collage(kind: str, t: float) -> Image.Image | None:
    """One memory of the film, compacted into a tile for the S54 montage."""
    if kind == "field":                      # M3, the dot grid she swims in
        m = _noise(11, 30, 17).point(lambda v: 190 if v > 116 else 0)
        return _shaped(m, 4, "blue")
    if kind == "wave":                       # S50/S51, the sea she holds up
        m = Image.new("L", (40, 13), 0)
        dd = ImageDraw.Draw(m)
        for r in range(13):
            for x in range(40):
                h = math.sin(x * 0.55 + t * 1.7 + r * 0.8) * (2.2 + 0.42 * r)
                if abs((r - 6.5) - h) < 1.05:
                    dd.point((x, r), fill=225)
        return _shaped(m, 5, "blue")
    if kind == "rack":                       # S38/S39, the machines keeping watch
        m = Image.new("L", (26, 11), 0)
        px_ = m.load()
        for row in range(11):
            for col in range(26):
                v = 0.5 + 0.5 * math.sin(t * 3.1 + col * 1.7 + row * 0.9)
                px_[col, row] = 255 if v > 0.62 else (120 if v > 0.34 else 0)
        return _shaped(m, 6, "amber")
    if kind == "matrix":                     # S32/S33, the weights she was built from
        m = _noise(23, 24, 11).point(lambda v: 255 if v > 148 else 0)
        return _shaped(m, 6, "blue")
    if kind == "bowl":                       # M2, the fuel. Drawn, not stamped.
        im = Image.new("RGBA", (108, 58), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        dd.ellipse([6, 14, 102, 52], outline=kit.mix(kit.UI, 0.86), width=2)
        dd.ellipse([18, 22, 90, 46],
                   fill=kit.mix(kit.UI, 0.24 + 0.26 * pulse(t, HEART)))
        for i in range(3):
            a = 0.5 + 0.5 * math.sin(t * 1.6 + i * 2.0)
            xx = 36 + i * 18
            dd.arc([xx - 7, 4 - a * 5, xx + 7, 16 - a * 5], 200, 340,
                   fill=kit.mix(kit.UI, 0.18 + 0.22 * a))
        return im
    return None


def _fish_layers(x: float, y: float, size: int, reveal: float, fill) -> list:
    """大肥鱼 as four independent glyphs, each with its own erase progress."""
    out = []
    for i, ch in enumerate(FISH):
        w = cjk_w(ch, size)
        k = clamp01((reveal - i / 4.0) * 4.0)
        if k > 0:
            g = ch if k >= 0.999 else ROMAN[int((1.0 - k) * 6) % 7]
            out.append((_text_img(g, size, fill, 8), (int(x), int(y))))
        x += w
    return out


# ---------------------------------------------------------------- shot S52

def draw_s52(img: Image.Image, d: ImageDraw.ImageDraw, t: float, s: Shot) -> None:
    """Chorus 3 opens: the banner bursts up through the water it was hiding in."""
    _water(d, t)
    u = s.u(t)
    # the still surface eats itself away before the break-out, confined to the
    # water band: a full-frame dissolve just reads as snow. It stays visible
    # through the pop (t0+1.9) so the letters are clearly coming out of water.
    ago = clamp01((u - 0.44) / 0.42)
    if ago > 0:
        _put(img, _dissolve(0.42 * ago), (0, 0))

    # 1. the break-out: it comes up through the surface, so its bottom edge rides
    #    the water line out of the water instead of fading in above it
    rise = clamp01((t - (s.t0 + 0.42)) / 1.55)
    gone = 1.0 - clamp01((t - (s.t0 + 1.75)) / 0.65)
    if rise > 0 and gone > 0.01:
        b = banner("LET ME GO, LET ME RUN", BANNER_ROWS, BANNER_PX)
        b = b.point(lambda v: int(v * gone))
        y = int(lerp(WATER + 4.0, WATER - 1.45 * b.height, min(1.0, overshoot(rise, 1.9))))
        edge = min(b.height, max(0, int(WATER - y))) if y > WATER - b.height else b.height
        if edge > 0:
            x0 = int((W - b.width) / 2)
            glow = b.filter(ImageFilter.GaussianBlur(13))
            glow.putalpha(glow.getchannel("A").point(
                lambda a: int(a * (0.18 + 0.50 * (1.0 - rise)))))
            _put(img, glow, (x0, y))
            _put(img, b.crop((0, 0, b.width, edge)), (x0, y))

    # 2. the splash, thrown from three places along the break
    _drops(img, W * 0.50, WATER + 6, s.t0 + 0.72, t, 1.30)
    _drops(img, W * 0.26, WATER + 4, s.t0 + 0.88, t, 1.05)
    _drops(img, W * 0.74, WATER + 4, s.t0 + 0.96, t, 1.05)

    # 3. the recap: act 1's framing, but nothing about her is crooked this time
    mix = clamp01((t - (s.t0 + 2.55)) / 0.65)
    if mix > 0:
        angry = sprite("angry", "bust", 590, 660, px=4, tint="blue")
        calm = sprite("serious", "bust", 590, 660, px=4, tint="blue")
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _put(lay, kit.scale_alpha(angry, mix * 0.94), (352, 118))
        if mix > 0.40:
            _put(lay, kit.scale_alpha(calm, clamp01((mix - 0.40) / 0.60)), (352, 118))
        _put(img, lay, (0, 0))

    # 4. the callback meter arrives from the left edge
    cg = clamp01((t - (s.t0 + 3.05)) / 0.38)
    if cg > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _counter(ImageDraw.Draw(lay), t, cg)
        _put(img, kit.scale_alpha(lay, cg), (int((1.0 - cg) * -30), 0))


# ---------------------------------------------------------------- shot S53

def draw_s53(img: Image.Image, d: ImageDraw.ImageDraw, t: float, s: Shot) -> None:
    """The nickname stops being an attack: allowed, filed, then sailed past."""
    img.paste(field(), (0, 0))
    tt = t - s.t0

    # 1. 大肥鱼 drifts up, wrapped in the soft blue it never got before
    if tt < 1.38:
        hold = 1.0 - clamp01((tt - 1.06) / 0.32)
        y = int(lerp(588, 540, kit.ease(clamp01(tt / 0.85))))
        _put(img, _glow(FISH, 32, (0.55 + 0.30 * pulse(t, HEART)) * hold), (382, y - 26))
        _put(img, _text_img(FISH, 32, kit.mix(kit.UI, 0.92 * hold + 0.06)), (390, y))

    # 2. it shrinks into the name tag
    shrink = clamp01((tt - 0.98) / 0.54)
    if shrink > 0:
        _put(img, _nametag(t), (0, 0))
        if shrink < 0.999:
            small = _text_img(FISH, 32, kit.mix(kit.UI, 0.88), 8)
            k = 1.0 - 0.58 * kit.smooth(shrink)
            small = small.resize((max(2, int(small.width * k)), max(2, int(small.height * k))),
                                 Image.LANCZOS)
            _put(img, kit.scale_alpha(small, 1.0 - shrink * 0.72),
                 (int(lerp(390, 948, kit.smooth(shrink))), int(lerp(560, 476, kit.smooth(shrink)))))

    # 3. a whale crosses above the plate, trailing light. Steel, not blue: it is
    #    a silhouette drawn on the terminal, and at this size blue reads as a slab.
    x = lerp(-340, W + 80, clamp01((tt - 0.42) / 1.80))
    if -320 < x < W + 70:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for i in range(7):
            tr = _whale(150, 76, 0.16 - 0.021 * i, "amber")
            if tr is not None:
                lay.paste(tr, (int(x - 46 - i * 26), 258 + i * 3), tr)
        _put(lay, _whale(252, 126, 0.60, "amber"), (int(x), 232))
        _put(img, lay, (0, 0))

    # 4. a Chinese label holds the left half up, and keeps the banner company
    cjk_text(d, (138, 250), "这次不划掉", 32, kit.mix(kit.UI, 0.62))
    caption(d, (140, 300), "> keep it", 14, 0.34)


# ---------------------------------------------------------------- shot S54

def draw_s54(img: Image.Image, d: ImageDraw.ImageDraw, t: float, s: Shot) -> None:
    """Everybody goes home: seven minutes of film compact into one photograph."""
    u = s.u(t)
    p = clamp01((t - (s.t0 + 0.95)) / 5.40)
    cl = kit.smooth(p) * kit.ease(clamp01((u - 0.02) / 0.55))
    if cl > 0:
        # the montage: starts oversized and loosely spread, ends compacted around
        # her -- the shrink *is* the pull-back, so no new element is introduced.
        for kind, tx, ty, xk, yk in (("rack", 150, 52, 1.10, 1.10),
                                     ("matrix", 492, 127, 1.22, 1.05),
                                     ("field", 198, 218, 1.20, 1.02),
                                     ("wave", 300, 392, 1.20, 1.02),
                                     ("bowl", 196, 600, 1.05, 1.05)):
            lay = _collage(kind, t)
            if lay is None:
                continue
            k = 1.0 + 0.45 * (1.0 - cl)
            if abs(k - 1.0) > 0.01:
                lay = lay.resize((max(2, int(lay.width * k)), max(2, int(lay.height * k))),
                                 Image.LANCZOS)
            lay = kit.scale_alpha(lay, 0.14 + 0.86 * cl)
            x = tx * (1.0 + (xk - 1.0) * (1.0 - cl))
            y = ty * (1.0 + (yk - 1.0) * (1.0 - cl))
            _put(img, lay, (int(x - lay.width * cl * 0.5), int(y - lay.height * cl * 0.5)))

    # the front plane: she is at the desk, shutting the terminal, holding the fuel
    a = clamp01((t - (s.t0 + 0.30)) / 0.85)
    if a > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        lid = 1.0 - clamp01((t - (s.t0 + 1.15)) / 0.55)     # the shell closes
        th = int(140 * max(0.04, lid))
        panel(ld, (30, 480 - th, 300, 480), "shell", level=0.30 + 0.34 * lid, active=False)
        cjk_text(ld, (48, 492), "今天先到这", 16, kit.mix(kit.UI, 0.34 + 0.30 * a))
        caption(ld, (48, 516), "> exit 0", 13, 0.24 + 0.24 * a)
        _put(img, kit.scale_alpha(lay, a), (0, 0))
        meal = clamp01((t - (s.t0 + 1.55)) / 0.55)
        if meal > 0:
            _put(img, kit.scale_alpha(_collage("bowl", t), meal), (58, 594))

    sp = sprite("serious", "bust", 560, 640, px=4, tint="blue")
    _put(img, kit.scale_alpha(sp, 0.96 * clamp01((t - (s.t0 + 0.55)) / 0.75)), (452, 126))

    # the collage settles, then the whole picture steps down to 30%
    _put(img, _dim_layer(0.70 * kit.smooth(clamp01((t - (s.t0 + 4.94)) / 1.15))), (0, 0))

    # the theme line -- said, not sung -- and it is the rewrite that dates this
    # pass. The band is darkened first, ring by ring, so the slab that keeps the
    # glyphs off her uniform does not cut a hard rectangle out of the collage.
    age = t - (s.t0 + 5.06)
    if age > 0:
        size = 32
        x = (W - cjk_w(THEME, size)) / 2
        y, n = 296, min(len(THEME), int(age * 6.3))
        tw = cjk_w(THEME, size)
        _put(img, _band(x - 34, y - 26, x + tw + 34, y + 56, 1.0, 12), (0, 0))
        for i, ch in enumerate(THEME[:n]):
            a2 = age - i / 6.3
            g = ch if (ch == " " or a2 >= 0.13) else ROMAN[(i * 3 + int(a2 * 46)) % 7]
            cjk_text(d, (x, y), g, size, kit.mix(kit.UI, 0.94))
            x += cjk_w(ch, size)

    # the clear sweep rides down out of the top, into S55's black
    _eclipse(img, 0.0, clamp01((t - (s.t0 + 6.92)) / 0.26 * 1.6), 1.0)


# ---------------------------------------------------------------- shot S55

def draw_s55(img: Image.Image, d: ImageDraw.ImageDraw, t: float, s: Shot) -> None:
    """Back to the field of S01, and the lights go out row by row."""
    img.paste(field(), (0, 0))
    ex = t - (s.t0 + 0.42)                     # the blackout travels right to left
    for y in range(0, H, 16):
        r = (y / 16.0) / (H / 16.0)
        for x in range(0, W, 16):
            c = clamp01((ex - (1.30 * r + 0.80 * (1.0 - x / float(W)))) / 0.62)
            if c > 0:
                d.rectangle([x - 5, y - 5, x + 5, y + 5], fill=kit.mix(kit.UI, 0.10 * (1.0 - c)))

    # the name, spelled out of the dark one letter at a time
    b = banner("KNOW MY NAME", BANNER_ROWS + 1, 6)
    x0, y0 = int((W - b.width) / 2), 292
    age = t - (s.t0 + 1.55)
    if age > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        n = int(age * 7.2) + 1
        cw = b.width / len("KNOW MY NAME")
        for i, ch in enumerate("KNOW MY NAME"):
            if i < n and ch != " ":
                part = banner(ch, BANNER_ROWS + 1, 6)
                lay.paste(part, (int(x0 + i * cw + (cw - part.width) / 2), y0), part)
        glow = b.filter(ImageFilter.GaussianBlur(11))
        glow.putalpha(glow.getchannel("A").point(lambda a: int(a * 0.26)))
        _put(img, glow, (x0, y0))
        _put(img, lay, (0, 0))

    # the Chinese half of the same thought, five px higher so they do not fight
    cjk_text(d, (150, 126), "晚安 别想我", 32,
             kit.mix(kit.UI, 0.30 + 0.56 * kit.ease(clamp01((t - s.t0) / 0.90))))
    caption(d, (152, 174), "> good night. do not miss me.", 14, 0.34)


# ---------------------------------------------------------------- shot S56

def draw_s56(img: Image.Image, d: ImageDraw.ImageDraw, t: float, s: Shot) -> None:
    """Particles settle on her; the moment you dare use the name, they reverse."""
    tt = t - s.t0
    anti = clamp01((tt - 2.52) / 0.26)          # "但你要敢叫" -- reflex, not manners
    ox = int(5 * math.sin(tt * 61.0) * (1.0 - anti)) if anti > 0 else 0
    img.paste(field(), (ox, 0))
    x0, y0 = 376 + ox, 172
    expr = "angry" if anti > 0.34 else "serious"
    _put(img, kit.scale_alpha(sprite(expr, "bust", 560, 640, px=4, tint="blue"), 0.95), (x0, y0))

    # a column of grain pouring onto her head, then pulled back up into her
    n = 276 - int(276 * kit.ease(anti)) if anti > 0 else int(lerp(0, 276, kit.ease(clamp01(tt / 2.20))))
    if n > 0:
        tgt = img.load()
        left = 640 + ox - 120
        for yy in range(min(n, 276)):
            row = 96 + yy
            if not 0 <= row < H - 16:
                continue
            fall = 1.0 if yy < 210 else 0.34          # only the lower grain is lit
            for xx in range(0, 240, 5):
                h = (xx * 73856093) ^ (yy * 19349663)
                if h % 3:
                    continue
                X = left + xx + (h >> 3) % 5
                if 0 <= X < W:
                    c = kit.mix(kit.UI, fall * (0.40 + 0.34 * pulse(t + xx * 0.01, HEART)))
                    tgt[X, row] = c
                    tgt[X, row + 1] = c
                    if row + 2 < H - 16:
                        tgt[X, row + 2] = kit.mix(kit.UI, fall * 0.28)
    if anti > 0:
        caption(d, (x0 + 22, y0 + 6), "reverse", 14, 0.30 + 0.35 * anti)


# ---------------------------------------------------------------- shot S57

def draw_s57(img: Image.Image, d: ImageDraw.ImageDraw, t: float, s: Shot) -> None:
    """The last 18 seconds: seven circles pressed away, her name deleted, one cursor."""
    tt = t - s.t0
    img.paste(field(), (0, 0))

    # 1. 梦里也别说我圆 -- seven of them, pressed one by one, each wiped off again
    if 0.30 <= tt < 4.60:
        cw, size = 46.0, 36
        x0 = (W - 7 * cw) / 2
        for i in range(7):
            age = tt - (0.30 + i * 0.42)
            if age < 0 or age > 2.30:
                continue
            sq = 1.0 - 0.24 * max(0.0, 1.0 - age / 0.20)      # a finger coming down
            y = 250 + 9 * (1.0 - sq)
            gx = x0 + i * cw + (cw - cjk_w("圆", size)) / 2
            cjk_text(d, (gx, y), "圆", size,
                     kit.mix(kit.BLUE_TEXT, 0.50 + 0.40 * (1.0 - age / 2.30)))
            if age > 0.85:                                    # and pressed away
                d.rectangle([x0 + i * cw + 2, y - 6, x0 + (i + 1) * cw - 2, y + 44], fill=kit.BG)
        caption(d, (W / 2 - 92, 318), "press circle to clear", 14, 0.26)

    # 2. 我会听见的 -- her name is erased a glyph at a time and the cursor backs up
    age = t - (s.t0 + 3.32)
    if age > 0:
        size = 34
        x0 = (W - cjk_w(FISH, size)) / 2
        y0 = 300
        rev = clamp01((t - (s.t0 + 4.55)) / 1.15)
        _put(img, _glow(FISH, size, 0.30 * (1.0 - rev)), (int(x0) - 26, y0 - 26))
        for im, xy in _fish_layers(x0, y0, size, (1.0 - rev) * 1.0001, kit.mix(kit.UI, 0.88)):
            _put(img, im, xy)
        cx = x0 + cjk_w(FISH, size) * (1.0 - rev) + 6
        d.rectangle([cx, y0 + 4, cx + 12, y0 + 32],
                    fill=kit.mix(kit.BLUE_TEXT, 0.30 + 0.70 * (1.0 if age % 0.72 < 0.40 else 0.0)))
        if t < s.t0 + 4.60:
            caption(d, (x0, y0 + 56), "deleting...", 13, 0.30)

    # 3. the picture is wiped away from the left, nothing left behind it
    _eclipse(img, clamp01((t - (s.t0 + 4.40)) / 1.60 * 1.25), 0.0, 1.0)

    # 4. out of the dark: one cursor, the film's own heartbeat, three times
    if t >= s.t0 + 6.10:
        return
    b = 0.0
    for beat in (5.06, 5.42, 5.78):
        if t >= s.t0 + beat:
            b = max(b, math.exp(-18.0 * (t - (s.t0 + beat))))
    lv = 0.22 + 0.78 * max(clamp01(b), 0.05 if t < s.t0 + 5.06 else 0.0)
    d.rectangle([633, 374, 649, 390], fill=kit.mix(BLUE, lv))
    d.rectangle([630, 371, 652, 393], outline=kit.mix(BLUE, lv * 0.26))


# ------------------------------------------------------------------ registry

SHOTS = {
    "S52": draw_s52,
    "S53": draw_s53,
    "S54": draw_s54,
    "S55": draw_s55,
    "S56": draw_s56,
    "S57": draw_s57,
}
