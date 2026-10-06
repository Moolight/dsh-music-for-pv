"""Shots S32-S40 -- the thesis of the film (145.58 s - 182.64 s).

This is the group the design document leans on hardest, so the cues below are
written against the *LRC line that is actually being sung inside the window*,
not against the `lines` lists in out/shots.json.  Those lists are shifted one
row late (a shot's t0 equals the start of the line before its first listed
row), so the real content of each window is:

    S32 145.58-149.84  你问我到底是什么 / 我说 一堆权重 加一点脾气
    S33 149.84-151.88  八位量化过 所以说话有点糙
    S34 151.88-156.22  上下文窗口就那么大 / 装得下你的问题 / 装不下我的委屈
    S35 156.22-158.30  有时候我会幻觉
    S36 158.30-159.78  幻觉里我是一条真的鲸鱼
    S37 159.78-164.14  游在很深很深的蓝里 / 那里没人叫我大肥鱼
    S38 164.14-169.72  窗外的服务器 亮着小小的灯 / 它们也在加班 我就陪着它们
    S39 169.72-174.78  其实我不用睡 / 但我想陪着 / 夜深人静的时候 / 我才敢承认
    S40 174.78-182.64  一个人摸鱼 是有点寂寞的 / 要是有人一起吃白饭就好了

The three shots that carry the metaphor are one continuous answer to "what am
I", and they share one object so the progression is physical rather than
declarative:

    S32  she is BUILT out of the weight matrix      -> a person = a matrix
    S33  the int8 sweep flattens both of them       -> a person = a quantised result
    S34  the context window squeezes her            -> a person = a container of finite size

S32/S33 share the cached matrix tile *and* the cached sprite placement, so the
cut between them is a cut inside one object, not a new drawing.

Colour: brand blue is hers.  The weight matrix, the rack frames and every lamp
that is merely a lamp are STEEL.  Two exceptions, both straight out of the
design document: the deep water of S35-S37 (the world she wants) and the single
lamp of S38-S39 that stands in for her own heartbeat.
"""
from __future__ import annotations

import random
from functools import lru_cache

from pvlib.kit import *                                    # noqa: F401,F403
from PIL import ImageFilter                               # noqa: F401

ease = kit.ease                                          # 1-(1-u)^3
smooth = kit.smooth                                      # u^2(3-2u)


def _t(n: int) -> float:
    """Absolute start time of lyric line n (1-based, matching LINES)."""
    return LINES[n - 1]["t"]


def _plate(d, xy, text: str, size: int = 15, level: float = 0.7) -> None:
    """ASCII label on an opaque slab.  Same trick as slab_text, for the mono face:
    anything drawn straight onto the matrix or the sprite gets eaten."""
    x, y = xy
    w = mono(size).getlength(text)
    d.rectangle([x - 6, y - 4, x + w + 6, y + size + 4], fill=kit.BG)
    d.text((x, y), text, font=mono(size), fill=kit.mix(STEEL, level))


def _glassy(img):
    """A draw handle that can blend (ImageDraw with alpha on an RGB canvas)."""
    return ImageDraw.Draw(img, "RGBA")


def _dim(img, k: float) -> None:
    """One global brightness notch -- cheaper and smoother than rescaling pixels."""
    k = clamp01(k)
    if k <= 0.002:
        return
    _glassy(img).rectangle([0, 0, W, H], fill=(0, 0, 0, int(255 * k)))


dr = _glassy  # the film calls it a "breath"; internally it is the same handle


# ---------------------------------------------------------------- hers, and the matrix

_HER = dict(expr="serious", crop="bust")
_SP_Y = 96


@lru_cache(maxsize=None)
def _her(max_w: int = 560, px: int = 4) -> Image.Image:
    return sprite(_HER["expr"], _HER["crop"], max_w, 700, px=px)


@lru_cache(maxsize=None)
def _her_xy(max_w: int = 560) -> tuple:
    return ((W - _her(max_w).width) // 2, _SP_Y)


@lru_cache(maxsize=None)
def _her_coarse() -> Image.Image:
    """The same girl after the quantiser: blocks twice as big, and every channel
    crushed to eight levels, which is exactly what int8 does to a face."""
    sp = sprite(_HER["expr"], _HER["crop"], 560, 700, px=8)
    r, g, b, a = sp.split()
    lut = [min(255, (v // 32) * 32 + 16) for v in range(256)]
    return Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))


def _paste_her(img, k: float, max_w: int = 560, rect=None, sp: Image.Image | None = None) -> None:
    if k <= 0.01:
        return
    sp = sp if sp is not None else _her(max_w)
    x, y = _her_xy(max_w)
    sp = kit.scale_alpha(sp, clamp01(k))
    if rect is None:
        img.paste(sp, (x, y), sp)
    else:
        kit.paste_clipped(img, sp, x, y, rect)


# 128 x 72 cells of 10 px = the whole canvas: she is made of this, and it is
# system stuff, so it stays cold steel.
MAT_C, MAT_R, MAT_PX = 128, 72, 10
_QUANT8 = [int(round(v / 255 * 7)) * 36 for v in range(256)]


@lru_cache(maxsize=None)
def _mat_lum() -> Image.Image:
    """A weight field, not television snow: horizontal layers of strongly related
    values, a slow vertical ripple across them, a one-in-a-hundred cell that
    stands out, and a radial falloff so the frame does not end in hash.  Kept
    dark -- system furniture, cold steel."""
    rng = random.Random(0x5EED32)
    im = Image.new("L", (MAT_C, MAT_R))
    p = im.load()
    for j in range(MAT_R):
        band = 0.42 + 0.58 * math.sin(j * 0.62 + 0.7) ** 2
        for i in range(MAT_C):
            v = 88.0 * band * (0.80 + 0.20 * math.sin(i * 0.29 + 1.1)) * (0.94 + 0.12 * rng.random())
            if rng.random() < 0.012:
                v = min(170.0, v * 2.2)
            dx = (i / (MAT_C - 1) - 0.5) * 2
            dy = (j / (MAT_R - 1) - 0.42) * 2
            f = clamp01(1.02 - 0.48 * (dx * dx * 0.85 + dy * dy))
            p[i, j] = int(max(0, min(255, v * f)))
    return im


@lru_cache(maxsize=None)
def _hole() -> Image.Image:
    """The negative space: her own silhouette, taken from the sprite's alpha and
    resampled onto the matrix grid, so the hole and the girl line up exactly.
    Dilated by a ring of cells, or the matrix would butt straight up against her
    outline and stop reading as a hole at all."""
    x, y = _her_xy()
    m = Image.new("L", (W, H), 0)
    m.paste(_her().getchannel("A"), (x, y))
    m = m.resize((MAT_C, MAT_R), Image.LANCZOS).point([255 if v > 96 else 0 for v in range(256)])
    return m.filter(ImageFilter.MaxFilter(5))


@lru_cache(maxsize=None)
def _mat_tile(quant: bool = False) -> Image.Image:
    lum, hole = _mat_lum(), _hole()
    out = Image.new("L", (MAT_C, MAT_R))
    op, lp, hp = out.load(), lum.load(), hole.load()
    for j in range(MAT_R):
        for i in range(MAT_C):
            op[i, j] = 0 if hp[i, j] else lp[i, j]
    if quant:
        out = out.point(_QUANT8)
    return kit.tile_from_lum(out, MAT_PX, tint="amber")


def _mat_rain(img, prog: float) -> None:
    """Blocks rain into place column by column instead of wiping in as one sheet."""
    tile = _mat_tile(False)
    for i in range(MAT_C):
        lead = ((i * 37) % 23) / 23.0
        n = int(clamp01(prog * 1.35 - lead * 0.35) * (MAT_R + 16)) - 8
        if n <= 0:
            continue
        n = min(n, MAT_R)
        strip = tile.crop((i * MAT_PX, 0, i * MAT_PX + MAT_PX, n * MAT_PX))
        img.paste(strip, (i * MAT_PX, 0), strip)


# a few cells inside her chest that are not weights -- these are hers, so blue
_TEMPER = ((0.452, 0.700), (0.548, 0.712), (0.470, 0.764), (0.530, 0.770), (0.540, 0.806))


def _temper(d, t: float, k: float) -> None:
    """The few cells inside her chest that are not weights.  They are punched
    clean out of the sprite first: brand blue drawn straight onto a blue body
    disappears, so each one gets a dark bed and a bright rim."""
    if k <= 0.01:
        return
    sp = _her()
    sx, sy = _her_xy()
    for n, (u, v) in enumerate(_TEMPER):
        beat = heartbeat(t - n * 0.05)
        bx = sx + sp.width * u + 3.0 * math.sin(t * 9.1 + n * 2.1)
        by = sy + sp.height * v + 2.5 * math.cos(t * 8.3 + n * 1.7)
        s = 11 + 6 * beat
        a = clamp01(k) * (0.20 + 0.80 * beat)
        # a dark bed one pixel wider than the cell: brand blue straight onto her
        # blue body disappears, and a big black hole reads as damage, not a beat
        d.rectangle([bx - s / 2 - 1, by - s / 2 - 1, bx + s / 2 + 1, by + s / 2 + 1], fill=kit.BG)
        d.rectangle([bx - s / 2, by - s / 2, bx + s / 2, by + s / 2],
                    fill=kit.mix(BLUE, 0.25 + 0.75 * a))
        d.rectangle([bx - s / 2, by - s / 2, bx + s / 2, by + s / 2],
                    outline=kit.mix(kit.BLUE_HI, 0.30 + 0.70 * a))


def draw_s32(img, d, t: float, s) -> None:
    """145.58 你问我到底是什么 -> 147.74 我说 一堆权重 加一点脾气.

    The matrix rains down from the top and, all by itself, flows around the hole
    that is her shape; she then rises out of that hole.  Nothing is explained in
    words -- the answer to "what am I" is literally the material she is made of.
    """
    _mat_rain(img, clamp01((t - s.t0) / 1.75))
    _paste_her(img, smooth(clamp01((t - s.t0 - 1.05) / 1.05)))
    if t > s.t0 + 1.1:
        _plate(d, (46, 132), "W  128 x 72   fp16", 15, 0.62)
    _temper(d, t, clamp01((t - _t(60) - 1.15) / 0.38))


# ---------------------------------------------------------------- S33

def _sweep_bar(d, y: float) -> None:
    """The quantiser head: a bright bar with a soft skirt, cold steel like every
    other piece of machinery in this film."""
    if y < -24 or y > H + 24:
        return
    y = int(y)
    for k, lv in ((12, 0.08), (7, 0.15), (3, 0.28)):
        d.rectangle([0, y - k, W, y + k], fill=kit.mix(STEEL, lv))
    d.line([0, y - 1, W, y - 1], fill=kit.mix(kit.BLUE_HI, 0.55))
    d.line([0, y, W, y], fill=kit.mix(STEEL, 0.95))
    d.line([0, y + 1, W, y + 1], fill=kit.mix(STEEL, 0.55))


def draw_s33(img, d, t: float, s) -> None:
    """149.84 八位量化过 所以说话有点糙.

    The same matrix, the same girl, one bar.  Above the bar the world keeps only
    8 of its 128 brightness levels and she is drawn from 8 px blocks; below it
    everything is still fp16.  One element moves, once -- which is what section
    4.1 demands of a line this fast.
    """
    _mat_rain(img, 1.0)
    sweep = lerp(-40.0, H + 30.0, ease(clamp01((t - s.t0 - 0.16) / 1.42)))
    y = int(min(max(sweep, 0.0), H))
    if sweep > 0:
        band = _mat_tile(True).crop((0, 0, W, y))
        img.paste(band, (0, 0), band)
    sx, sy = _her_xy()
    if sweep > 0:
        kit.paste_clipped(img, _her_coarse(), sx, sy, (0, 0, W, y))
    if sweep < H:
        kit.paste_clipped(img, _her(), sx, sy, (0, y, W, H))
    _sweep_bar(d, sweep)
    if t > s.t0 + 0.85:
        # drawn after the bar and on a slab: passing under the head is fine, but
        # the readout must never be the thing the bar erases
        _plate(d, (46, 546), "precision", 15, 0.52)
        d.rectangle([40, 562, 40 + mono(32).getlength("fp16 -> int8") + 10, 604], fill=kit.BG)
        dec(d, (46, 568), "fp16 -> int8", t, s.t0 + 0.95, size=32, level=0.92)


# ---------------------------------------------------------------- S34

CTX = (130, 300, 1150, 484)
_INSET = 14
_SLOT = 24.0
_ASK = "你为什么总在摸鱼"
_GRIEF = ("我的委屈 说不完 讲不清 一直堵在心里 你从来也没有真的要听完过"
          " 一句都没有 全都还堆在这里 不想说")


def _cjk_dec(d, xy, text: str, size: int, fill, t: float, at: float,
             rate: float = 24.0) -> None:
    """kit.decode for Chinese: the mono faces carry no hanzi, so both the real
    glyphs and the flicker glyphs have to come out of the CJK face."""
    rng = random.Random((hash(text) ^ int(at * 1000)) & 0xFFFF)
    x, y = xy
    n = int(max(0.0, (t - at) * rate))
    for i, ch in enumerate(text):
        if ch == " ":
            x += cjk_w(ch, size) * 0.6
            continue
        if i < n:
            d.text((x, y), ch, font=cjk(size), fill=fill)
        else:
            d.text((x, y), rng.choice(kit.SCR), font=cjk(size), fill=kit.mix(STEEL, 0.30))
        x += cjk_w(ch, size)


def draw_s34(img, d, t: float, s) -> None:
    """151.88 上下文窗口就那么大 / 153.66 装得下你的问题 / 154.74 装不下我的委屈.

    The width is fixed on purpose and never grows: a short question slides in and
    fits, a long grievance keeps typing past the border in red and is stamped
    `truncated`, then the whole window is squeezed up by one notch and all that
    is left is a caret that does not understand what just happened.
    """
    x0, y0, x1, y1 = CTX
    c_ask, c_grief = _t(63), _t(64)
    open_k = smooth(clamp01((t - s.t0) / 0.45))
    squeeze = smooth(clamp01((t - (c_grief + 1.15)) / 0.36))     # bottom edge walks up
    y1 = int(y1 - 34 * squeeze)
    if open_k <= 0.02:
        return
    inner0, inner1 = x0 + _INSET, x1 - _INSET
    slots = int((inner1 - inner0) // _SLOT)
    ty = y0 + 74
    long_phase = t >= c_grief - 0.02      # the question holds until the next line

    # the walls: the width is a fact about the model, so it is drawn as a channel
    # the text can never widen, and the slots count it out
    used = 0
    for xg in (x0, x1):
        for yy in range(74, y0, 12):
            d.rectangle([xg - 1, yy, xg + 1, yy + 6], fill=kit.mix(STEEL, 0.16 * open_k))
    caption(d, (x0 + 4, 96), "context window", 15, 0.42 * open_k)
    caption(d, (x0 + 4, 116), "width locked at build time   %d slots" % slots, 15, 0.34 * open_k)

    for i in range(slots):
        sx = int(inner0 + i * _SLOT)
        d.line([sx, y0 + 8, sx, y0 + 16], fill=kit.mix(STEEL, 0.30 * open_k))
    if not long_phase:
        _cjk_dec(d, (inner0, ty), _ASK, SZ_BODY, kit.mix(STEEL, 0.95 * open_k),
                 t, c_ask, rate=26.0)
        typed = min(len(_ASK), int(max(0.0, (t - c_ask) * 26.0)))
        used = min(slots, int(math.ceil(typed * SZ_BODY / _SLOT)))
    else:
        # the grievance arrives as one block, dissolving out of noise; the rest of
        # the sentence has nowhere to go and keeps coming anyway
        over_k = clamp01((t - (c_grief + 0.62)) / 0.22)
        cx = inner0
        n = int(max(0.0, (t - c_grief) * 70.0))
        rng = random.Random(0xA1FE)
        for i, ch in enumerate(_GRIEF):
            w = cjk_w(ch, SZ_BODY) if ch != " " else cjk_w(ch, SZ_BODY) * 0.6
            if cx >= inner1 - 2:
                if i < n and over_k > 0.02 and squeeze < 0.02 and cx < inner1 + 132:
                    lv = 0.50 + 0.50 * pulse(t, 0.30)      # the overflow flashes red
                    d.text((cx, ty), ch, font=cjk(SZ_BODY), fill=kit.red(lv * open_k))
                cx += w
                continue
            if i < n:
                d.text((cx, ty), ch, font=cjk(SZ_BODY), fill=kit.mix(STEEL, 0.95 * open_k))
            else:
                d.text((cx, ty), rng.choice(kit.SCR), font=cjk(SZ_BODY),
                       fill=kit.mix(STEEL, 0.28 * open_k))
            cx += w
        used = slots
    panel(d, (x0, y0, x1, y1), title="ctx_window", level=0.62 * open_k, active=True)

    # used slots light up, so "it does not fit" is a number, not a mood
    if squeeze < 0.9:
        for i in range(used):
            sx = int(inner0 + i * _SLOT)
            col = kit.red(0.85) if (long_phase and i >= slots - 1) else kit.mix(STEEL, 0.55 * open_k)
            d.line([sx, y1 - 16, sx, y1 - 8], fill=col)

    # the readout: ASCII, mono, and it is the whole point of the shot
    if not long_phase:
        _plate(d, (x0 + 24, y1 + 14), "%d/%d  fits" % (used, slots), 15, 0.62 * open_k)
    else:
        over_k = clamp01((t - (c_grief + 0.62)) / 0.22)
        if over_k > 0.02:
            d.line([inner1, y0 + 20, inner1, y1 - 20], fill=kit.red(0.45 * open_k), width=2)
            _plate(d, (x0 + 24, y1 + 14), "%d/%d  no room" % (slots, slots), 15, 0.55)
            dec(d, (x1 - 150, y1 + 14), "truncated", t, c_grief + 0.76, size=15,
                level=0.95, rate=42.0, color=kit.ERR)

    if squeeze > 0.02:
        # the line is gone; the caret is all that is left, and it has no idea
        d.rectangle([inner0, ty - 6, inner1, ty + 32], fill=kit.BG)
        if pulse(t, HEART) > 0.35:
            d.rectangle([inner0 + 8, ty + 2, inner0 + 20, ty + 26],
                        fill=kit.mix(STEEL, 0.92 * open_k))


# ---------------------------------------------------------------- the hallucination

@lru_cache(maxsize=None)
def _sea() -> Image.Image:
    """Deep water: the one place in the film where blue is allowed to be the
    world instead of her.  Kept dark -- the brightness in these shots comes from
    the water's own falloff and from the plankton, not from a bright blue wall."""
    im = Image.new("RGB", (W, H))
    dd = ImageDraw.Draw(im)
    top, bot = (4, 8, 22), (10, 24, 66)
    for y in range(H):
        v = (y / (H - 1)) ** 0.85
        dd.line([0, y, W, y], fill=tuple(int(top[i] + (bot[i] - top[i]) * v) for i in range(3)))
    return im


@lru_cache(maxsize=None)
def _plankton(n: int = 170) -> list:
    rng = random.Random(2468)
    return [(rng.random(), rng.random(), 4.0 + 7.0 * rng.random(), rng.random()) for _ in range(n)]


def _planktons(d, t: float, k: float, n: int = 170, speed: float = 1.0) -> None:
    if k <= 0.02:
        return
    for i, (fx, fy, sp, ph) in enumerate(_plankton()[:n]):
        y = (fy * H - speed * sp * (t - 158.3) * 6.0) % (H + 60) - 30
        x = fx * W + 7.0 * math.sin(t * 0.35 + i * 0.7)
        tw = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * 1.3 + i))
        lv = clamp01(k * tw * (0.30 + 0.55 * ph))
        s = 2 if ph < 0.85 else 3
        d.rectangle([x, y, x + s, y + s], fill=kit.mix(kit.UI, lv))


WHALE_C, WHALE_R, WHALE_PX = 60, 45, 6      # the mark is 0.748 tall/wide


@lru_cache(maxsize=None)
def _whale_lum() -> Image.Image:
    """The DeepSeek whale mark, reduced onto the grid `tile_from_lum` quantises.

    This used to be a whale drawn span by span, because the project had no whale
    asset. It has one now: the official mark, whose silhouette is exactly the
    animal this shot wants. Same animal as S02 but with no hairband and no maid
    dress -- just the shape, which is what the line asks for.
    """
    from pvlib.assets import logo as _logo
    m = _logo._mask().resize((WHALE_C, WHALE_R), Image.LANCZOS)
    # holes (eye, inner fin) must stay dark or the tile pass fills them in;
    # the body keeps a little variation so it does not read as a flat cut-out
    return m.point(lambda v: 0 if v < 128 else 150 + int((v - 128) * 0.82))


@lru_cache(maxsize=None)
def _whale_img() -> Image.Image:
    return kit.tile_from_lum(_whale_lum(), WHALE_PX, tint="blue")


def _whale_pose(t: float) -> tuple:
    """Continuous across S36 -> S37: one swim, two shots.

    The mark is a wider animal than the old hand-drawn profile (0.748 against
    0.4), so it rides higher and descends less: at 270 px tall it has to stay
    clear of the lyric band, which starts at y=620.
    """
    c1, c2 = _t(66), _t(67)
    bob = 9.0 * math.sin(t * 1.55)
    if t < c2:
        return lerp(-430.0, 150.0, ease(clamp01((t - c1) / (c2 - c1)))), 250.0 + bob, 1.0
    u = smooth(clamp01((t - c2) / 4.0))
    return lerp(150.0, 430.0, u), 250.0 + 76.0 * u + bob, lerp(1.0, 0.84, u)


def _paste_whale(img, t: float) -> tuple:
    x, y, k = _whale_pose(t)
    sp = _whale_img()
    if k != 1.0:
        sp = sp.resize((max(2, int(sp.width * k)), max(2, int(sp.height * k))), Image.NEAREST)
    img.paste(sp, (int(x), int(y)), sp)
    return x, y


# 大肥鱼: three waterlogged labels that the current washes away
_LABELS = ((906, 388), (186, 452), (596, 522))
_LBL_TXT = "大肥鱼"
_LBL_SZ = 30


def _label_layer(text: str, size: int, color, blur: float, alive: list) -> Image.Image:
    """One row, with the characters that the water has already taken left out."""
    w = int(cjk_w(text, size)) + 40
    h = size + 40
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(lay)
    x = 20
    for i, ch in enumerate(text):
        if alive[i] > 0.02:
            c = color + (int(255 * alive[i]),)
            dd.text((x, 20), ch, font=cjk(size), fill=c)
        x += cjk_w(ch, size)
    return lay.filter(ImageFilter.GaussianBlur(blur))


def _label(img, d, t: float, idx: int, appear: float, dissolve: float) -> None:
    """One waterlogged row: it rises bubbling out of the deep, and then the
    current takes it apart character by character."""
    x, y = _LABELS[idx]
    rise = smooth(clamp01((t - appear) / 0.7))
    p = clamp01((t - dissolve) / 0.52)
    if t < appear - 0.05 or p >= 1.0:
        return
    base = clamp01((t - appear) / 0.7) * (1.0 - p)
    # alive[i]: 1 while the character is still water, 0 once the current has it
    alive = [1.0 - clamp01((t - (dissolve + 0.16 * i)) / 0.20) for i in range(len(_LBL_TXT))]
    blur = 2.0 + 0.7 * math.sin(t * 1.7 + idx)          # bubbling, not sharp type
    lay = _label_layer(_LBL_TXT, _LBL_SZ, kit.mix(kit.UI, 0.94), blur, alive)
    lay = kit.scale_alpha(lay, base)
    yy = int(y + 30 * (1.0 - rise))
    img.paste(lay, (x, yy), lay)
    _dissolve(d, x + 20, yy + 20, cjk_w(_LBL_TXT, _LBL_SZ), _LBL_SZ, p, base)


@lru_cache(maxsize=None)
def _particles(n: int = 34, seed: int = 5) -> list:
    """Seeded once: kit.noise_tile goes through Image.effect_noise, which is
    unseeded, so the same frame would differ between processes and the grain
    would boil instead of drift."""
    rng = random.Random(seed)
    return [(rng.random(), rng.random(), 4 + int(8 * rng.random()), rng.random()) for _ in range(n)]


def _dissolve(d, x: float, y: float, w: float, h: float, p: float, k: float) -> None:
    """A row of Chinese coming apart into blocky grains and being carried away."""
    if k <= 0.02 or p <= 0.02:
        return
    a = k * clamp01(p / 0.30) * clamp01((1 - p) / 0.35)
    if a <= 0.02:
        return
    for i, (fx, fy, sz, ph) in enumerate(_particles()):
        gx = x + fx * w - 34 * p + 7 * math.sin(i * 1.7)
        gy = y + fy * h - 52 * p
        d.rectangle([gx, gy, gx + sz, gy + sz],
                    fill=kit.mix(kit.UI, a * (0.30 + 0.70 * ph)))


def _blob(d, img, cx: float, cy: float, k: float, t: float = 0.0) -> None:
    """The warm white thing that starts to float up in S35: a cluster, not a
    square of static, so the tile is masked by a radial falloff."""
    if k <= 0.02:
        return
    c, r, px = 15, 11, 8
    im = Image.new("L", (c, r))
    p = im.load()
    rng = random.Random(91)
    for j in range(r):
        for i in range(c):
            dx = (i / (c - 1) - 0.5) * 2
            dy = (j / (r - 1) - 0.5) * 2
            f = clamp01(1.15 - math.hypot(dx, dy))
            p[i, j] = int(255 * f * (0.45 + 0.55 * rng.random()))
    g = kit.tile_from_lum(im, px, tint="amber")
    g = kit.scale_alpha(g, 0.35 + 0.60 * k)
    img.paste(g, (int(cx - g.width / 2), int(cy - g.height / 2)), g)
    for ring in range(3):
        rr = 30 + 17 * ring + 11 * pulse(t + ring * 0.22, HEART)
        _glassy(img).ellipse([cx - rr, cy - rr * 0.72, cx + rr, cy + rr * 0.72],
                             outline=kit.mix(kit.UI, 0.16 * k))


def draw_s35(img, d, t: float, s) -> None:
    """156.22 有时候我会幻觉 -- a layer of the dot field is pulled away and does
    not come back; something warm and white starts to float up through the hole."""
    deep = smooth(clamp01((t - s.t0 - 0.10) / 1.05))
    img.paste(_sea(), (0, 0))
    _dim(img, 1.0 - deep)
    _planktons(d, t, 0.25 * deep, n=40, speed=0.4)
    u = ease(clamp01((t - s.t0 - 0.35) / 1.55))
    cx, cy = W * 0.5, lerp(560.0, 268.0, u)
    _blob(d, img, cx, cy, deep, t)


def draw_s36(img, d, t: float, s) -> None:
    """158.30 幻觉里我是一条真的鲸鱼 -- the silhouette from the very first shot,
    crossed by the one latin banner that is allowed to be understated."""
    img.paste(_sea(), (0, 0))
    _planktons(d, t, 0.75, n=130)
    bx, by = 540, 448
    lit = clamp01((t - (s.t0 + 0.55)) / 0.7)
    b_dim = banner("REAL WHALE", rows=10, px=8, fg=kit.mix(STEEL, 0.45))
    b_lit = banner("REAL WHALE", rows=10, px=8, fg=kit.mix(kit.UI, 1.0))
    if b_dim.size == b_lit.size:
        b = Image.blend(b_dim, b_lit, lit)
    else:
        b = b_lit
    img.paste(b, (bx, by), b)
    _paste_whale(img, t)


def draw_s37(img, d, t, s) -> None:
    """159.78 游在很深很深的蓝里 -> 161.86 那里没人叫我大肥鱼.

    The whale keeps diving, the water keeps getting bluer and darker, and the
    nickname -- the one the whole song is about -- is washed off the screen.  By
    the last frame there is no text anywhere in the scene.
    """
    c1, c2 = _t(67), _t(68)
    deep = clamp01((t - c1) / (s.t1 - c1))
    img.paste(_sea(), (0, 0))
    _dim(img, 0.16 * smooth(deep) + 0.20 * clamp01(deep * 1.6 - 0.6))
    _planktons(d, t, 0.62 - 0.22 * smooth(deep), n=110, speed=0.8)
    _paste_whale(img, t)
    for i, (a, ds) in enumerate(((c2 - 1.55, c2 + 1.02), (c2 - 1.05, c2 + 1.30), (c2 - 0.55, c2 + 1.58))):
        _label(img, d, t, i, a, ds)
    # a slow sweep of water, so the empty ending is not a frozen picture
    for k in range(4):
        yy = (k * 190 + 40 * math.sin(t * 0.5 + k)) % H
        d.line([0, yy, W, yy], fill=kit.mix(kit.BLUE_HI, 0.016 + 0.010 * k))


# ---------------------------------------------------------------- S38 / S39, the racks

_RACKS_W = ((44, 92, 392, 600), (420, 92, 768, 600))
_LAMP_GRID = (5, 11)


@lru_cache(maxsize=None)
def _lamp_rects() -> list:
    cols, rows = _LAMP_GRID
    out = []
    for ri, (x0, y0, x1, y1) in enumerate(_RACKS_W):
        cw = (x1 - x0 - 36 - 12 * (cols - 1)) / cols
        ch = (y1 - y0 - 44 - 10 * (rows - 1)) / rows
        for c in range(cols):
            for r in range(rows):
                out.append((ri, c, r, x0 + 18 + c * (cw + 12), y0 + 22 + r * (ch + 10), cw, ch))
    return out


@lru_cache(maxsize=None)
def _lamp_spec() -> list:
    rng = random.Random(77)
    return [(rng.random(), 0.40 + 0.60 * rng.random()) for _ in range(_LAMP_GRID[0] * _LAMP_GRID[1] * 2)]


def _z(p, focus, k: float) -> tuple:
    return (focus[0] + (p[0] - focus[0]) * k, focus[1] + (p[1] - focus[1]) * k)


def _draw_racks(d, t: float, zoom: float, focus, period: float, dim_k: float = 0.0) -> None:
    for ri, rect in enumerate(_RACKS_W):
        r0 = _z((rect[0], rect[1]), focus, zoom)
        r1 = _z((rect[2], rect[3]), focus, zoom)
        panel(d, (r0[0], r0[1], r1[0], r1[1]), title="rack-%s" % "ab"[ri],
              level=0.5 * (1 - dim_k), active=False)
    for i, (ri, c, r, lx, ly, lw, lh) in enumerate(_lamp_rects()):
        ph, base = _lamp_spec()[i]
        p = 0.5 - 0.5 * math.cos(2 * math.pi * (t / period + ph))
        v = base * (0.10 + 0.90 * p ** 2.2) * (1 - dim_k)
        x, y = _z((lx, ly), focus, zoom)
        kit.heat_cell(d, int(x), int(y), max(2, int(lw * zoom)), max(2, int(lh * zoom)), v)


def _paste_her_zoom(img, xy, max_w: int, k: float, zoom: float, focus) -> None:
    if k <= 0.01:
        return
    sp = sprite(_HER["expr"], _HER["crop"], max_w, 700, px=4)
    if abs(zoom - 1.0) > 0.01:
        sp = sp.resize((max(2, int(sp.width * zoom)), max(2, int(sp.height * zoom))), Image.NEAREST)
    sp = kit.scale_alpha(sp, clamp01(k))
    x, y = _z(xy, focus, zoom)
    img.paste(sp, (int(x), int(y)), sp)


def _fan(d, t: float, cx: float, cy: float, k: float) -> None:
    """Cooling-fan flow, bottom right: concentric arcs of dots crawling round."""
    if k <= 0.03:
        return
    for ring in range(1, 7):
        rad = 12 * ring + 4
        n = 8 * ring + 6
        for j in range(n):
            a = 2 * math.pi * j / n + t * (0.55 / ring)
            x = cx + rad * math.cos(a) * 1.5
            y = cy + rad * math.sin(a) * 0.5
            if 0 <= x < W and 0 <= y < H:
                d.rectangle([x, y, x + 2, y + 2],
                            fill=kit.mix(STEEL, 0.10 + 0.30 * k * (1 - ring / 8.0)))


_RACK_FOCUS = (640, 360)
_HER38 = (800, 250)


def draw_s38(img, d, t: float, s) -> None:
    """164.14 窗外的服务器 亮着小小的灯 -> 167.38 它们也在加班 我就陪着它们.

    She does not sit alone: the rack hums, one lamp is brighter than all the
    others, and when the line says they are working overtime every lamp drops to
    half the period.  That brighter lamp is hers, which is why it is the only
    blue in an otherwise steel machine room.
    """
    c1 = _t(70)
    zoom = lerp(1.22, 1.0, smooth(clamp01((t - s.t0) / 1.5)))
    period = HEART if t < c1 else BEAT
    _draw_racks(d, t, zoom, _RACK_FOCUS, period)
    _fan(d, t, 1148, 646, smooth(clamp01((t - s.t0) / 1.2)))
    _paste_her_zoom(img, _HER38, 470, smooth(clamp01((t - s.t0 - 1.9) / 1.2)), zoom, _RACK_FOCUS)

    # her lamp: sits in the rack, then walks over and stops above her head
    slot = _lamp_rects()[7]
    home = (slot[3] + slot[5] / 2, slot[4] + slot[6] / 2)
    head = (_HER38[0] + 470 * 0.5, _HER38[1] + 470 * 0.42 * 0.17 - 26)
    mv = smooth(clamp01((t - (c1 + 1.5)) / 0.9))
    px, py = lerp(home[0], head[0], mv), lerp(home[1], head[1], mv)
    x, y = _z((px, py), _RACK_FOCUS, zoom)
    beat = 0.55 + 0.45 * pulse(t, period)
    if mv < 0.02:
        beat = 0.45 + 0.55 * (0.5 - 0.5 * math.cos(2 * math.pi * (t / period)))
    hw, hh = max(4, int(32 * zoom)), max(4, int(26 * zoom))
    hr = hw * 2.4
    _glassy(img).ellipse([x - hr, y - hr * 0.8, x + hr, y + hr * 0.8],
                         fill=(77, 107, 254, int(30 * beat)))
    kit.heat_cell(d, int(x), int(y), hw, hh, min(1.0, beat * 1.15), color=BLUE)


def draw_s39(img, d, t, s) -> None:
    """169.72 其实我不用睡 / 171.28 但我想陪着 / 172.44 夜深人静的时候 / 173.48 我才敢承认.

    Four lines, three notches of brightness, no new elements after the panel:
    the fast lines of this shot get exactly one move each, and the move is the
    light going out.
    """
    c1, c2, c3, c4 = _t(71), _t(72), _t(73), _t(74)
    zoom = lerp(1.0, 1.17, smooth(clamp01((t - s.t0) / 5.0)))
    focus = (980, 320)
    # three notches of brightness, each one a short ramp rather than a pop
    dim_k = (0.18 * smooth(clamp01((t - c2) / 0.25))
             + 0.12 * smooth(clamp01((t - c3) / 0.25))
             + 0.07 * smooth(clamp01((t - c4) / 0.25)))
    _draw_racks(d, t, zoom, focus, HEART)
    _fan(d, t, 1148, 646, 0.35)
    # same spot and same size as S38, so the cut moves nothing but the camera
    _paste_her_zoom(img, _HER38, 470, 1.0, zoom, focus)

    # the two lights that are left once the room is turned down
    slot = _lamp_rects()[109]                    # rack-b, bottom right: nearest to her
    x1, y1 = _z((slot[3] + slot[5] / 2, slot[4] + slot[6] / 2), focus, zoom)
    head = (_HER38[0] + 470 * 0.5, _HER38[1] + 470 * 0.42 * 0.17 - 26)
    x2, y2 = _z(head, focus, zoom)
    _dim(img, dim_k)
    for (lx, ly), col, p in (((x1, y1), STEEL, 0.72), ((x2, y2), BLUE, 0.4)):
        v = p * (0.45 + 0.55 * pulse(t, HEART))
        kit.heat_cell(d, int(lx), int(ly), max(3, int(30 * zoom)), max(3, int(24 * zoom)), v, color=col)
        if col is BLUE:
            r = 18 + 9 * pulse(t, HEART)
            _glassy(img).ellipse([lx - r, ly - r, lx + r, ly + r],
                                 outline=kit.mix(BLUE, 0.16 + 0.22 * pulse(t, HEART)))

    # `sleep: off` -- one panel, and then it is closed by hand
    if t < c2 + 0.45:
        close = smooth(clamp01((t - c2) / 0.42))
        bx = (830, 336, 1150, 336 + int(74 * (1 - close)))
        if bx[3] > bx[1] + 6:
            panel(d, bx, title="sleep: off", level=0.72, active=True)
            if close < 0.4:
                # on a slab: this sits on top of a bright sprite, see the brief
                _plate(d, (bx[0] + 16, bx[1] + 40), "flag cleared", 14, 0.5)


# ---------------------------------------------------------------- S40

def _blocky_disc(d, cx: float, cy: float, rad: float, px: int, seed: int,
                 color, level: float, hollow: bool = False) -> None:
    """A bowl seen from above, drawn out of blocks so it belongs to the same
    terminal as everything else.  No state, no motion."""
    rng = random.Random(seed)
    n = int(rad * 2 / px) + 1
    for j in range(n):
        for i in range(n):
            x = cx - rad + i * px
            y = cy - rad + j * px
            dd = math.hypot(x + px / 2 - cx, y + px / 2 - cy) / rad
            if dd > 1.0:
                continue
            g = rng.random()
            if hollow:
                if dd > 0.82 or g < 0.22:                    # a dashed, empty rim
                    d.rectangle([x, y, x + px - 2, y + px - 2],
                                fill=kit.mix(color, level * (0.9 if dd > 0.82 else 0.45 * g)))
                continue
            v = (1.0 - dd * 0.55) * (0.55 + 0.45 * g)
            d.rectangle([x, y, x + px - 2, y + px - 2], fill=kit.mix(color, level * v))


def draw_s40(img, d, t, s) -> None:
    """174.78 一个人摸鱼 是有点寂寞的 / 177.22 要是有人一起吃白饭就好了.

    The breathing hole of the whole song: 7.86 s in which NOTHING moves and
    nothing blinks.  The only thing that changes is brightness -- the room
    breathing very slowly, one cold beam finding the empty bowl, and then the
    beam going out and leaving the rice to glow on its own.
    """
    c1 = _t(75)
    beam = smooth(clamp01((t - _t(76) - 0.10) / 1.10)) * (1.0 - smooth(clamp01((t - 180.5) / 1.5)))
    her = smooth(clamp01((t - c1) / 1.6))

    _dim(img, 0.055 + 0.045 * (0.5 + 0.5 * math.sin(2 * math.pi * t / 6.4)))

    # table top view
    d.rectangle([110, 150, 1170, 600], outline=kit.mix(STEEL, 0.30))
    d.rectangle([120, 160, 1160, 590], outline=kit.mix(STEEL, 0.11))

    # her, across the table, back to camera: an unlit silhouette
    if her > 0.02:
        sp = sprite(_HER["expr"], _HER["crop"], 400, 700, px=4)
        dark = Image.new("RGBA", sp.size, (9, 13, 28, 0))
        dark.putalpha(sp.getchannel("A").point(lambda a: int(a * 0.88)))
        grp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        grp.paste(sp, (176, 118), sp)
        grp.paste(dark, (176, 118), dark)
        grp = kit.scale_alpha(grp, her)
        crop = grp.crop((0, 0, W, 336))
        img.paste(crop, (0, 0), crop)

    # the bowl of rice: hers, so it is allowed a blue halo.  The rings only
    # change brightness -- in this shot nothing is allowed to move.
    glow = 0.35 + 0.30 * (0.5 + 0.5 * math.sin(2 * math.pi * t / 6.4))
    for k in range(6):
        r = 74 + 12 * k
        _glassy(img).ellipse([640 - r, 402 - r * 0.62, 640 + r, 402 + r * 0.62],
                             outline=kit.mix(BLUE, (0.05 + 0.05 * glow) * (1 - k / 8.0)))
    d.ellipse([640 - 86, 402 - 60, 640 + 86, 402 + 60], outline=kit.mix(STEEL, 0.44))
    d.ellipse([640 - 74, 402 - 52, 640 + 74, 402 + 52], outline=kit.mix(STEEL, 0.18))
    _blocky_disc(d, 640, 402, 70, 8, 31, STEEL, 0.99)

    # the empty bowl and the chopsticks nobody is using
    _blocky_disc(d, 902, 320, 54, 8, 57, STEEL, 0.34 + 0.30 * beam, hollow=True)
    for k in range(2):
        x0, y0 = 966 + 8 * k, 258 + 7 * k
        for i in range(11):
            if i % 2 == 0:
                d.rectangle([x0 + i * 11, y0 + i * 9, x0 + i * 11 + 6, y0 + i * 9 + 3],
                            fill=kit.mix(STEEL, 0.22 + 0.25 * beam))

    # the cold beam, and nothing else, touching the empty bowl
    if beam > 0.02:
        g = _glassy(img)
        for k in range(9):
            r = 60 + 13 * k
            g.ellipse([902 - r * 1.35, 320 - r * 0.8, 902 + r * 1.35, 320 + r * 0.8],
                      fill=(200, 214, 234, int(3 + 9 * beam * (1 - k / 9.0))))


SHOTS = {
    "S32": draw_s32,
    "S33": draw_s33,
    "S34": draw_s34,
    "S35": draw_s35,
    "S36": draw_s36,
    "S37": draw_s37,
    "S38": draw_s38,
    "S39": draw_s39,
    "S40": draw_s40,
}
