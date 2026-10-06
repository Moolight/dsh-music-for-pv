"""Shots S17-S31 -- act 4 tail (86.04-118.02) and all of act 5 (118.02-145.58).

Group 2 of five; see SHOTS.md sections 4 and 5. Everything here is a pure
function of the absolute song time `t`, so the frames can be rendered out of
order and in parallel.

Design notes that drove the code
--------------------------------
* SHOTS.md's coverage column runs one line ahead of the real LRC for this
  stretch: shot k's window is exactly the LRC interval of the lines listed for
  shot k-1.  The shot *windows* (shots.json / SHOTS.md time column) are correct
  and contiguous, so they are used as-is; every beat inside a window is anchored
  to the absolute times SHOTS.md gives and to the real LRC line times (e.g. S23
  tries column 4 at 119.95 so the MISS lands under 「缓存未命中」), never to
  `s.line_at`, which returns the wrong line here.
* The temperature (S26/S27) and score (S28) panels are one shot later in the
  libretto than their windows: S26's window still sings 「是 world.feed(me)」.
  The shots keep the numbers SHOTS.md assigns them, but the panel reaches 0.70
  as late as it can (129.2) and S27 only pushes past 0.70 after 0.6 s, so the
  order/chaos turn lands on 「再高一点 我就开始胡说」 rather than early.
* SHOTS.md describes the cache columns as turning brand blue.  Task rule 1 and
  SHOTS.md 4.4 rule 3 both say system elements stay cold steel, and the cache /
  token counter / VRAM bar are named in that rule, so they are drawn in bright
  steel; the only blue on a panel here is the 0.2 s hand-off cursor and things
  that are hers (rice, her hand, the heartbeat cursor, the corrected
  world.feed line).
* One active panel at a time (rule 2): every panel that is not the one the shot
  is about is drawn with `active=False` (36%) and holds still.  The switch
  between panels is a 0.2 s cursor blink, never two panels animating at once.
* The very short lines (S25's two 1.06 s halves, S28's 1.32 s) get exactly one
  element doing one displacement, nothing else.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

from pvlib.kit import *

# ---------------------------------------------------------------- local palette
# STEEL (=kit.UI, cold white steel) is the system.  BLUE is her: her body, her
# hand, the rice she eats, the heartbeat cursor.  Nothing else may be blue.
GRN = (118, 214, 152)        # "stable" / "PASS" readouts, the only third colour
PURP = (104, 22, 74)         # S27's purple-red drift

_ease = kit.ease


def steel(lv: float = 1.0):
    return kit.mix(STEEL, lv)


def hers(lv: float = 0.95):
    return kit.blue(lv)


# ---------------------------------------------------------------- small parts

def _blink(t: float, period: float = 0.2) -> bool:
    return int(t / period) % 2 == 0


def handoff_cursor(d, x, y, t, size: int = 16, lv: float = 0.95):
    """The 0.2 s blink that covers a panel hand-off (never two panels moving)."""
    if _blink(t, 0.2):
        caption(d, (x, y), "_", size, lv, BLUE)


def cursor_block(d, x, y, t, w: int = 20, h: int = 7, lv: float = 1.0):
    """M7: her heartbeat cursor, 1.21 s breathing period."""
    k = 0.34 + 0.66 * pulse(t, HEART, 0.0, 1.0)
    d.rectangle([x, y, x + w, y + h], fill=kit.mix(BLUE, lv * k))


def rice_dot(d, x, y, s: int = 3, lv: float = 0.95):
    d.rectangle([x, y, x + s - 1, y + s - 1], fill=kit.mix(BLUE, lv))


def rice_pile(d, cx, cy, n: int = 9, seed: int = 3, spread: int = 16, lv: float = 0.9):
    rng = random.Random(seed)
    for _ in range(n):
        rice_dot(d, cx + rng.randint(-spread, spread), cy + rng.randint(-spread // 2, spread // 2),
                 3, lv * rng.uniform(0.6, 1.0))


def _blk(d, x, y, col, n: int = 2):
    d.rectangle([x, y, x + n, y + n], fill=col)


def icon_fish(d, cx, cy, k: float = 1.0, lv: float = 0.85, blue: bool = False, n: int = 2):
    col = hers(lv) if blue else steel(lv)
    step = max(4, int(7 * k))
    for i in range(-5, 6):
        for j in range(-2, 3):
            if (i / 5.2) ** 2 + (j / 2.1) ** 2 <= 1.0:
                _blk(d, cx + i * step, cy + j * step, col, n)
    for i in range(1, 4):
        for j in range(-i, i + 1):
            if i - abs(j) < 2 or i >= 3:
                _blk(d, cx - (5 + i) * step, cy + j * step, col, n)


def icon_bowl(d, cx, cy, k: float = 1.0, lv: float = 0.9, n: int = 2):
    step = max(4, int(6 * k))
    col = kit.mix(BLUE, lv)
    for j in range(0, 4):
        w = 5 - j
        for i in range(-w, w + 1):
            if j >= 2 and abs(i) < w:
                continue
            _blk(d, cx + i * step, cy + j * step, col, n)
    for i in range(-3, 4):
        for j in range(-1, -4, -1):
            if abs(i) + abs(j + 1) <= 3:
                _blk(d, cx + i * step, cy + j * step, kit.mix(BLUE, 1.0), n)


def icon_chili(d, x, y, n: int = 12, step: int = 7, lv: float = 0.85):
    for i in range(n):
        yy = y + int(3 * math.sin(i * 0.6))
        d.rectangle([x + i * step, yy, x + i * step + 3, yy + 5], fill=kit.mix(kit.RED, lv))


def finger_bar(d, x, y, down: float, w: int = 26, h: int = 9):
    d.rectangle([x, y + down, x + w, y + down + h], fill=kit.mix(BLUE, 0.55 + 0.4 * down))


def blockman(d, x, y, h: int = 300, lv: float = 0.34, tilt: float = 0.0):
    """The boss: a big blocky halfblock-ish silhouette (system, so steel)."""
    col = steel(lv)
    hd = int(h * 0.14)
    tx = int(tilt * hd * 0.6)
    d.rectangle([x - hd + tx, y, x + hd + tx, y + int(h * 0.28)], fill=col)             # head
    d.rectangle([x - int(h * 0.09), y + int(h * 0.28), x + int(h * 0.09), y + int(h * 0.32)],
                fill=col)                                                               # neck
    d.rectangle([x - int(h * 0.25), y + int(h * 0.32), x + int(h * 0.25), y + int(h * 0.70)],
                fill=col)                                                               # torso
    for a, b in ((-0.34, -0.25), (0.25, 0.34)):                                        # arms
        d.rectangle([x + int(h * a), y + int(h * 0.35),
                     x + int(h * b), y + int(h * 0.68)], fill=col)
    for a, b in ((-0.19, -0.04), (0.04, 0.19)):                                        # legs
        d.rectangle([x + int(h * a), y + int(h * 0.70), x + int(h * b), y + h], fill=col)


def hand(d, x, y, k: float = 1.0, lv: float = 0.85):
    """Her left hand (she is the blue one), palm plus four fingers."""
    col = kit.mix(BLUE, lv)
    w, h = int(120 * k), int(70 * k)
    d.rectangle([x, y, x + w, y + h], fill=col)
    for i in range(4):
        fx = x + int((8 + i * 28) * k)
        d.rectangle([fx, y - int(52 * k), fx + int(18 * k), y + 4], fill=col)
    d.rectangle([x - int(26 * k), y + int(8 * k), x + 4, y + int(58 * k)], fill=col)
    d.rectangle([x + w - 4, y + int(30 * k), x + w + int(30 * k), y + int(62 * k)], fill=col)


def dash_rect(d, box, color, dash: int = 9, gap: int = 7):
    x0, y0, x1, y1 = box
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1),
                             (x1, y1, x0, y1), (x0, y1, x0, y0)):
        n = max(1, int(math.hypot(bx - ax, by - ay) // (dash + gap)))
        for i in range(n + 1):
            u0 = i * (dash + gap)
            u1 = min(u0 + dash, math.hypot(bx - ax, by - ay))
            if u1 <= u0:
                continue
            L = math.hypot(bx - ax, by - ay) or 1.0
            d.line([ax + (bx - ax) * u0 / L, ay + (by - ay) * u0 / L,
                    ax + (bx - ax) * u1 / L, ay + (by - ay) * u1 / L], fill=color)


def jitter_box(d, box, level, jx: float, jy: float, seed: int, color=None):
    x0, y0, x1, y1 = box
    rng = random.Random(seed)
    col = kit.mix(color or STEEL, level)
    edges = ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0))
    for e, (ax, ay, bx, by) in enumerate(edges):
        ox, oy = rng.uniform(-jx, jx), rng.uniform(-jy, jy)
        d.line([ax + ox, ay + oy, bx + ox * 0.4, by + oy], fill=col)


def noise_lum(cols: int, rows: int, seed: int) -> Image.Image:
    rng = random.Random(seed)
    im = Image.new("L", (cols, rows))
    im.putdata([rng.randrange(256) for _ in range(cols * rows)])
    return im


def noise_tile(cols: int, rows: int, px: int, seed: int, tint: str = "amber") -> Image.Image:
    """Deterministic stand-in for kit.noise_tile (which is unseeded/impure)."""
    return kit.tile_from_lum(noise_lum(cols, rows, seed), px, tint)


def tint_frame(img, color, alpha: float):
    if alpha <= 0.004:
        return
    a = max(0, min(255, int(255 * alpha)))
    mask = Image.new("L", (W, H), a)
    img.paste(color, (0, 0), mask)


def carve_cjk(img, x, y, txt, size, fill, prog):
    """Chinese strokes being cut in, left to right (S21's 手艺)."""
    prog = clamp01(prog)
    if prog <= 0:
        return
    f = cjk(size)
    w = int(f.getlength(txt)) + 4
    h = size + 10
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text((0, 0), txt, font=f, fill=255)
    cut = max(1, min(w, int(w * prog)))
    solid = Image.new("RGB", (cut, h), fill)
    img.paste(solid, (x, y), m.crop((0, 0, cut, h)))
    if cut < w:
        d = ImageDraw.Draw(img)
        d.line([x + cut, y, x + cut, y + h], fill=kit.mix(BLUE, 0.35))


def jitter_cjk(d, x, y, txt, size, fill, amp: float, seed: int):
    """Per-character displacement -- S27's hanzi coming apart."""
    rng = random.Random(seed)
    cx = x
    for ch in txt:
        d.text((cx + rng.uniform(-amp, amp), y + rng.uniform(-amp, amp)),
               ch, font=cjk(size), fill=fill)
        cx += cjk(size).getlength(ch) + (rng.uniform(-amp, amp) if amp > 0.6 else 0)


# ---------------------------------------------------------------- canned text

CODE = (
    "def forward(x, w, b):",
    "    return x @ w.T + b",
    "loss = cross_entropy(logits, y)",
    "grad = tape.gradient(loss, params)",
    "opt.apply(grad); params -= lr * grad",
    "if step % 100 == 0:",
    "    log(loss.item(), cache.hit)",
    "ctx = ctx[-8192:]",
    "tokens += len(prompt) + 1",
    "if cache.miss: refill(ctx)",
    "assert out.shape == (1, 4096)",
    "yield tokenizer.decode(ids)",
    "for k, v in state.items():",
    "    attn[k] = softmax(v / temp)",
    "return ModelOutput(last_hidden)",
    "with torch.no_grad():",
    "    logits = model(x, ctx)",
    "kv_cache.append(k, v, layer)",
    "sampler.temperature = 0.70",
    "while not done: next_token()",
    "prof = cuda.event(elapsed_time)",
    "if oom: raise BudgetError",
)


# ================================================================ S17
# 86.04-89.34   LET ME GO marquee crossing 摸鱼, two dot icons, print("hello world")
def _plaque(d, x, y, txt, size, fill, color=(11, 16, 30)):
    """Opaque slab with a little air around the glyphs (`slab_text` is tight and
    its BG fill vanishes inside the banner's dark mortar)."""
    w = cjk_w(txt, size)
    d.rectangle([x - 12, y - 10, x + w + 12, y + size + 10], fill=color)
    d.rectangle([x - 12, y - 10, x + w + 12, y - 9], fill=kit.mix(BLUE, 0.35))
    d.text((x, y), txt, font=cjk(size), fill=fill)


def draw_s17(img, d, t, s):
    p = t - s.t0
    u = clamp01(p / 2.30)                      # a marquee runs at a constant rate
    sp = banner("LET ME GO", rows=24, px=7, fg=steel(0.7), bg=BG, max_w=1240)
    kit.paste_clipped(img, sp, int(lerp(W + 20, -sp.width - 20, u)), 286, (0, 96, W, 610))
    # 摸鱼 is what she does, so brand blue; it crosses the banner, hence the plaque.
    _plaque(d, int(lerp(-260, W + 120, u)), 344, "摸鱼", 52, hers(0.95))

    pi = p - 2.14
    if pi > 0:
        b = int(pi / 0.24)
        both = pi > 0.96
        if both or b in (0, 2):
            icon_fish(d, 420, 400, 1.7, 0.9, n=3)
        if both or b in (1, 3):
            icon_bowl(d, 870, 400, 1.7, 0.95, n=3)
    if p > 2.5:
        caption(d, (470, 520), ">", 18, 0.7)
        dec(d, (492, 520), 'print("hello world")', t, s.t0 + 2.55, size=18, level=0.95, rate=20)


# ================================================================ S18
# 89.34-93.12   the late-night office again: she types, code comes out, it pans away
S18_TAPS = (0.36, 0.70, 1.04)
S18_TYPE = (0.36, 0.70, 1.04, 1.26, 1.46, 1.62, 1.76)


def draw_s18(img, d, t, s):
    p = t - s.t0
    pan = _ease(clamp01((p - 1.86) / 1.60))
    ddy, tdy, rdy = int(pan * 560), int(pan * 460), int(pan * 380)

    if pan < 0.999:
        sp = kit.scale_alpha(sprite("serious", "bust", 420, 560), 1.0 - pan)
        img.paste(sp, (56, 118 + int(pan * 620)), sp)

    panel(d, (300, 330 + ddy, 1010, 480 + ddy), "desk", 0.48)
    panel(d, (520, 180 + tdy, 960, 342 + tdy), "terminal", 0.62)
    for i, at in enumerate(S18_TYPE):
        if p >= at:
            dec(d, (544, 202 + tdy + i * 22), CODE[i], t, s.t0 + at, size=14, level=0.78, rate=26)
    panel(d, (250, 392 + rdy, 344, 472 + rdy), "rice", 0.48)
    rice_pile(d, 297, 440 + rdy, 10, 11, 15, 0.9)

    # three finger taps on the keyboard (the keyboard is part of the desk)
    for i, at in enumerate(S18_TAPS):
        down = 6.0 * (1.0 - clamp01((p - at) / 0.14)) if p >= at else 0.0
        if p < 1.30:
            finger_bar(d, 660 + i * 62, 356 + ddy, down)

    if p > 3.02:
        k = clamp01((p - 3.02) / 0.22)
        if k > 0.05:
            cursor_block(d, 614, 330, t, 28, 8, k)


# ================================================================ S19
# 93.12-102.88   terminal / assets split screen, the boss walks in, she switches
S19_ASSETS = (("rice", 190), ("fish", 310), ("chili", 430))


def draw_s19(img, d, t, s):
    p = t - s.t0
    switched = p > 5.46                      # 98.58: her hand lands
    dis = clamp01((p - 5.46) / 0.34)         # right panel dissolving
    lv = 0.55

    panel(d, (70, 100, 600, 592), "terminal", lv)
    panel(d, (690, 100, 1215, 592), "assets", lv if not switched else lv * 0.7)

    # --- left: waiting prompt, then a wall of pretend code
    if not switched:
        caption(d, (100, 150), "$", 18, 0.7)
        if _blink(t, 0.6):
            caption(d, (124, 150), "_", 18, 0.95, BLUE)
        caption(d, (100, 190), "awaiting input", 14, 0.4)
    else:
        n = min(15, max(1, int((p - 5.46) / 0.012) + 1))     # the panel fills instantly
        for i in range(n):
            caption(d, (100, 136 + i * 28), CODE[(i * 3) % len(CODE)], 15, 0.72)
        if p > 5.72 and _blink(t, 0.44):
            d.rectangle([100, 136 + n * 28, 110, 136 + n * 28 + 6], fill=kit.mix(BLUE, 0.95))

    # --- right: the loot, then noise
    if not switched:
        for name, y in S19_ASSETS:
            if name == "rice":
                icon_bowl(d, 750, y + 26, 1.2, 0.95)
                rice_pile(d, 776, y + 6, 6, 5, 12, 0.8)
            elif name == "fish":
                icon_fish(d, 760, y + 20, 1.2, 0.8)
            else:
                icon_chili(d, 726, y + 14, 10, 7, 0.8)
            caption(d, (836, y + 10), "%s  x%d" % (name, 1), 16, 0.55)
    else:
        nr = int(472 * dis)
        if nr > 0:
            sp = noise_tile(130, 118, 4, 77, "amber")
            sp2 = sp.copy()
            a2 = sp2.getchannel("A")
            m = a2.copy()
            m.paste(255, [0, 0, m.width, nr])
            ImageDraw.Draw(m).rectangle([0, nr, m.width, m.height], fill=0)
            sp2.putalpha(ImageChops.multiply(a2, m))
            kit.paste_clipped(img, kit.scale_alpha(sp2, 0.62), 694, 104, (690, 100, 1216, 592))
        caption(d, (740, 560), "assets: lost", 16, 0.5)

    # --- the boss walks in from the left edge at 97.0
    if p > 3.88:
        bu = clamp01((p - 3.88) / 1.55)
        bx = int(lerp(-170, 250, _ease(bu)))
        bob = int(4 * math.sin(p * 6.0)) if bu < 1 else 0
        blockman(d, bx, 296 + bob, 300, 0.36)

    # --- her left hand presses (blue: it is her), then withdraws
    if p > 5.10:
        hu = clamp01((p - 5.10) / 0.36)
        back = _ease(clamp01((p - 6.35) / 0.55))
        hy = int(lerp(lerp(660, 470, _ease(hu)), 700, back))
        hand(d, 560, hy, 1.0, 0.85 * (1 - back))
        if 5.42 < p < 6.20:
            r = int(30 * clamp01((p - 5.42) / 0.5)) + 4
            d.ellipse([620 - r, 520 - r // 2, 620 + r, 520 + r // 2], outline=kit.mix(BLUE, 0.6))
            d.ellipse([620 - r // 2, 520 - r // 4, 620 + r // 2, 520 + r // 4],
                      outline=kit.mix(BLUE, 0.35))


# ================================================================ S20
# 102.88-108.22  code scrolls three screens, a rice block flashes, the boss asks
def draw_s20(img, d, t, s):
    p = t - s.t0
    scroll = p * 190.0
    panel(d, (120, 90, 780, 520), "terminal", 0.6)

    i0 = int(scroll // 22) - 1
    for j in range(20):
        i = i0 + j
        y = 112 + i * 22 - scroll
        if y < 108 or y > 508:
            continue
        if i in (36, 50):
            near = 1.0 - min(1.0, abs(y - 300) / 34.0)
            if near > 0:
                for a in range(6):
                    for b in range(3):
                        d.rectangle([160 + a * 9, y - 8 + b * 9, 166 + a * 9, y - 4 + b * 9],
                                    fill=kit.mix(BLUE, 0.25 + 0.75 * near))
                if near > 0.6:
                    caption(d, (228, y - 10), "rice_block", 14, 0.55, BLUE)
                continue
        if i < 0:
            continue
        caption(d, (150, y), CODE[i % len(CODE)], 15, 0.68)

    # her fingers, then they stop dead at 107.34
    pause = p > 4.46
    for i in range(3):
        if pause and p < 4.86:
            down = 5.0 if _blink(t, 0.4) else 0.0
        else:
            down = 5.0 * (1.0 - clamp01((p * 2.6 + i * 0.3) % 1.0 / 0.3))
        finger_bar(d, 300 + i * 62, 560, down)

    # the boss peeks over the right shoulder, tilts his head at 106.5
    blockman(d, 1010, 300, 300, 0.34, tilt=1.0 if p > 3.62 else 0.0)

    if p > 4.47:
        bu = _ease(clamp01((p - 4.47) / 0.34))
        bx = int(lerp(1290, 800, bu))
        panel(d, (bx, 152, bx + 336, 232), "boss", 0.62)
        cjk_text(d, (bx + 22, 172), "> 你在干嘛", 24, steel(0.85))


# ================================================================ S21
# 108.22-114.00  the inference panel: the curve crawls, PASS, 手艺 is carved
def draw_s21(img, d, t, s):
    p = t - s.t0
    sl = _ease(clamp01(p / 0.42))
    x0 = int(lerp(1500, 180, sl))
    panel(d, (x0, 100, x0 + 920, 540), "inference", 0.6)
    if sl < 0.999:
        return

    # one column per frame: the climb is deliberately glacial
    cols = 800 // 6
    step = int(p / 0.0406)
    prog = min(0.92, step * 0.9 / cols)
    last = kit.dot_chart(d, 240, 190, 800, 280,
                         lambda u: 0.22 + 0.30 * u + 0.045 * math.sin(u * 7.0),
                         prog, steel(0.88), sx=6, sy=6)
    caption(d, (240, 146), "step %07d" % (1238 + step), 15, 0.6)
    caption(d, (470, 146), "ctx 8192", 15, 0.5)
    caption(d, (640, 146), "tok/s 0.83", 15, 0.5)
    caption(d, (790, 146), "temp 0.70", 15, 0.5)
    # flat, unshakable noise floor: same height every frame, never a jitter
    for i in range(48):
        base = 486 - (2 if i % 9 == 0 else 0)
        d.rectangle([252 + i * 12, base, 258 + i * 12, 490], fill=steel(0.42))
    caption(d, (240, 500), "variance 0.0000  (steady)", 15, 0.55)

    if p >= 4.50:                                  # 112.72 「你看 我又赢了」
        if last:
            lx, ly = last
            d.line([lx, ly, lx, ly - 30], fill=steel(0.8))
            for k in range(3):
                d.rectangle([lx + 2, ly - 30 + k * 9, lx + 26, ly - 24 + k * 9], fill=steel(0.9))
        caption(d, (985, 128), "PASS", 20, 0.95, GRN)

    # boss still leaving the frame at the left (continuity with S20)
    if p < 1.30:
        blockman(d, int(lerp(700, 120, _ease(clamp01(p / 1.1)))), 300, 300, 0.30)
    if 0.0 <= p < 0.95:
        panel(d, (700, 150, 1036, 230), "boss", 0.55)
        cjk_text(d, (722, 170), "> 你在干嘛", 24, steel(0.8))

    # 手艺, carved stroke by stroke, at the very end (S22 opens on it)
    if p > 5.05:
        carve_cjk(img, 880, 448, "手艺", 40, steel(0.95), (p - 5.05) / 0.72)


# ================================================================ S22
# 114.00-118.02  手艺 glows, the whole window shrinks to an icon, 别声张, one blue dot
S22_ICON = (1020, 400, 1160, 505)


def draw_s22(img, d, t, s):
    p = t - s.t0
    if p < 1.15:
        g = 0.5 + 0.5 * pulse(t, HEART)
        for i, r in enumerate((150, 118, 88)):
            d.ellipse([640 - r * 1.9, 300 - r, 640 + r * 1.9, 300 + r],
                      outline=kit.mix(BLUE, 0.10 + 0.10 * i + 0.10 * g))
        slab_text(d, (540, 272), "手艺", 44, steel(0.95), pad=12)
        return

    k = _ease(clamp01((p - 1.10) / 1.45))            # 115.10 -> 116.55
    gone = fade_out(clamp01((p - 3.16) / 0.80), 0.55)   # the icon dissolves to a dot
    x0 = int(lerp(140, S22_ICON[0], k))
    y0 = int(lerp(90, S22_ICON[1], k))
    x1 = int(lerp(1140, S22_ICON[2], k))
    y1 = int(lerp(560, S22_ICON[3], k))
    if p < 3.34:
        panel(d, (x0, y0, x1, y1), "fish.exe", (0.5 * (1.0 - 0.3 * k)) * gone + 0.05)
        size = int(44 * (1 - k) + 20 * k)
        if size >= 18:
            tx = (x0 + x1) // 2 - int(cjk_w("手艺", size) / 2)
            if k < 0.55 or p < 3.0:
                cjk_text(d, (tx, (y0 + y1) // 2 - size // 2), "手艺", size,
                         steel(0.6 + 0.4 * gone))
        else:
            icon_bowl(d, x0 + 26, y1 - 24, 0.6, 0.9 * max(0.2, gone))
            icon_fish(d, x1 - 34, y1 - 22, 0.55, 0.75 * max(0.2, gone), blue=True)

    if p >= 2.55:
        nlv = fade_out(clamp01((p - 3.16) / 0.80), 0.55)
        panel(d, (S22_ICON[0] - 46, S22_ICON[1] - 26, S22_ICON[0] + 150,
                  S22_ICON[1] + 44), "note", 0.62 * nlv + 0.06)
        slab_text(d, (S22_ICON[0] - 32, S22_ICON[1] - 8), "别声张", 20,
                  steel(0.9 * nlv + 0.1), pad=6)

    if p > 3.10:
        cursor_block(d, 1078, 452, t, 22, 8, 0.95)

    wi = clamp01((p - 3.42) / 0.58)                  # 117.42 -> 118.00 清场
    if wi > 0:
        wipe(img, min(0.999, wi))
    if p > 3.34:
        cursor_block(d, 1078, 452, t, 22, 8, 0.9)


# ================================================================ S23
# 118.02-122.48  cache panel (1/7) -> hand-off -> token counter (2/7)
S23_C0, S23_R0, S23_CW, S23_CH = 118, 152, 74, 58
S23_COL = (118.90, 119.28, 119.66)


def _cache_cell(i, j):
    x = S23_C0 + i * (S23_CW + 6)
    y = S23_R0 + j * (S23_CH + 6)
    return x, y, x + S23_CW, y + S23_CH


def draw_s23(img, d, t, s):
    p = t - s.t0
    a_cache = p < 2.33                     # cache is the active panel until 120.35
    dim = 1.0 if a_cache else 0.36
    lv = 0.6 * (1.0 if a_cache else 0.72)
    panel(d, (90, 112, 762, 486), "cache", lv)

    miss_t = 2.12                          # 120.14
    for i in range(8):
        for j in range(5):
            x0, y0, x1, y1 = _cache_cell(i, j)
            fin = clamp01((p - 0.10 - (i + j) * 0.035) / 0.34)   # assembling
            v = 0.17 * fin
            col = STEEL
            if i <= 2 and p >= S23_COL[i] - 118.02:
                v = 0.94
            elif i <= 2 and p >= S23_COL[i] - 118.02 - 0.30:
                r = int((p - (S23_COL[i] - 118.02 - 0.30)) / 0.062)
                if j == min(4, r):
                    v = 1.0
            elif i == 3 and miss_t <= p < miss_t + 0.26:
                v = 0.95
                col = kit.RED
            elif i == 3 and p >= miss_t + 0.26:
                v = 0.10
                col = kit.ERR
            kit.heat_cell(d, x0, y0, x1 - x0, y1 - y0, v * dim, col)
    if p >= miss_t + 0.20:
        caption(d, (S23_C0 + 3 * 80 + 4, S23_R0 + 2), "MISS", 20, 0.95 if a_cache else 0.8, kit.ERR)
    if a_cache:
        caption(d, (96, 122), "ctx 8192/8192", 14, 0.5)
    else:
        caption(d, (96, 122), "ctx 8192/8192", 14, 0.24)

    # ---- hand-off: one 0.2 s blink, then the token counter takes over
    if 2.00 <= p < 2.42:
        handoff_cursor(d, 790, 296, t, 22, 0.95)

    if p >= 2.33:
        a_tok = clamp01((p - 2.33) / 0.30)
        tx = int(lerp(1340, 900, _ease(a_tok)))
        panel(d, (tx, 112, tx + 330, 250), "tokens", 0.6)
        n = int(40 * (p - 2.33))
        caption(d, (tx + 20, 148), "%06d" % n, 30, 0.98, (206, 220, 240))
        caption(d, (tx + 20, 196), "tok/s 40.0", 14, 0.5)
        # the burn bar under it, charring left to right
        burn = int((p - 2.33) * 13)
        for i in range(22):
            x = tx + 20 + i * 14
            v, col = 0.30, STEEL
            if i < burn - 1:
                v, col = 0.06, STEEL
            elif i == burn - 1:
                v, col = 1.0, kit.RED
            elif i == burn:
                v, col = 0.75, kit.RED
            kit.heat_cell(d, x, 218, 11, 20, v, col)


# ================================================================ S24
# 122.48-124.24  V4-Flash against V4-Pro (3/7): speed vs thinking
def draw_s24(img, d, t, s):
    p = t - s.t0
    panel(d, (110, 140, 600, 520), "V4-Flash", 0.62)
    panel(d, (680, 140, 1170, 520), "V4-Pro", 0.75, active=False)
    d.line([640, 120, 640, 540], fill=steel(0.22))

    prog = clamp01((p - 0.12) / 0.48)
    kit.dot_chart(d, 150, 200, 410, 240, lambda u: 1.0 - 0.55 * (1 - u) ** 2,
                  prog, steel(0.95), sx=6, sy=6)
    caption(d, (150, 452), "speed 100", 18, 0.95)

    progc = 0.10 + 0.07 * clamp01((p - 0.12) / 1.60)
    kit.dot_chart(d, 720, 200, 410, 240, lambda u: 0.30 + 0.10 * u,
                  progc, steel(0.5), sx=6, sy=6)
    dots = "." * (1 + int((p - 0.12) / 0.34) % 3)
    caption(d, (720, 452), "thinking" + dots, 18, 0.6)

    cursor_block(d, 596, 330, t, 18, 8, 0.95)


# ================================================================ S25
# 124.24-126.62  world.execute(me) -> world.feed(me).  One element, one move.
S25_A, S25_STRIKE, S25_SWAP, S25_RISE = "world.execute(me)", 1.32, 1.76, 2.06


def draw_s25(img, d, t, s):
    p = t - s.t0
    f = mono_b(40)
    shake = 0.0
    if S25_STRIKE <= p < S25_SWAP:
        u = (p - S25_STRIKE) / (S25_SWAP - S25_STRIKE)
        shake = 4.0 * (1 - u) * (1 if int((p - S25_STRIKE) * 24) % 2 else -1)
    rise = int(lerp(0, 22, _ease(clamp01((p - S25_RISE) / 0.34))))
    txt = S25_A if p < S25_RISE else "world.feed(me)"
    col = steel(0.95) if p < S25_RISE else kit.blue(1.0)
    x = 640 - f.getlength(txt) / 2
    y = 296 - rise + shake

    if p < S25_RISE:
        d.text((x, y), "world.", font=f, fill=steel(0.95))
        ex = x + f.getlength("world.")
        d.text((ex, y), "execute", font=f, fill=steel(0.72))
        d.text((ex + f.getlength("execute"), y), "(me)", font=f, fill=steel(0.95))
        if p >= S25_STRIKE:
            d.line([ex - 2, y + 26, ex + f.getlength("execute") + 2, y + 26],
                   fill=kit.mix(kit.RED, 0.9), width=3)
    else:
        d.text((x, y), txt, font=f, fill=col)

    if S25_STRIKE <= p < S25_RISE:
        # the new token is written over the old one from the right end backwards
        cu = clamp01((p - S25_SWAP) / 0.30)
        if cu > 0:
            rng = random.Random(int(p * 24))
            new = "feed"
            fx = 640 - f.getlength("world.feed(me)") / 2 + f.getlength("world.")
            n = int(cu * 4)
            for i in range(n):
                ch = new[i] if (i < n - 1 or cu >= 1) else rng.choice(kit.SCR)
                d.rectangle([fx + i * f.getlength("d"), y - 2, fx + (i + 1) * f.getlength("d"), y + 44],
                            fill=BG)
                d.text((fx + i * f.getlength("d"), y), ch, font=f, fill=kit.blue(0.9))

    if p >= S25_RISE:
        d.line([x - 4, y + 46, x + f.getlength(txt) + 4, y + 46], fill=kit.mix(BLUE, 0.5))


# ================================================================ S26
# 126.62-129.54  temperature panel (4/7): the cursor settles on 0.70, everything snaps
S26_BOX = (330, 228, 950, 500)


def _s26_ticks():
    if not hasattr(_s26_ticks, "cache"):
        rng = random.Random(20261006)
        out = []
        for gy in range(52, 612, 34):
            for gx in range(40, 1252, 34):
                if 300 < gx < 990 and 190 < gy < 540:
                    continue
                out.append((gx, gy, rng.uniform(-11, 11), rng.uniform(-11, 11)))
        _s26_ticks.cache = out
    return _s26_ticks.cache


def draw_s26(img, d, t, s):
    p = t - s.t0
    # 0.6 s of continuity: the corrected line from S25 drifts away
    if p < 0.62:
        fo = 1.0 - clamp01(p / 0.62)
        f = mono_b(40)
        txt = "world.feed(me)"
        d.text((640 - f.getlength(txt) / 2, 218 - 46 * p), txt, font=f, fill=kit.blue(0.75 * fo))

    snap_t, arrive = 2.28, 2.28
    val = lerp(0.93, 0.70, _ease(clamp01(p / arrive)))
    snapped = p >= snap_t
    k = clamp01((p - snap_t) / 0.12)

    # the frame was scattered before the snap, exactly orthogonal after it
    pts = []
    for gx, gy, dx, dy in _s26_ticks():
        ox, oy = dx * (1 - k), dy * (1 - k)
        vx = dx * 0.55 * (1 - k) + 5 * k
        vy = dy * 0.55 * (1 - k)
        for n in range(7):
            pts.append((gx + ox + vx * n / 6.0, gy + oy + vy * n / 6.0))
    d.point(pts, fill=steel(0.40 + 0.35 * k))

    lv = 0.62 if snapped else 0.55
    panel(d, S26_BOX, "temperature", lv)
    cjk_text(d, (368, 268), "温度", 24, steel(0.85))
    caption(d, (470, 258), "%.2f" % val, 34, 0.98)
    bx0, bx1, by = 380, 900, 352
    n = 26
    cw = (bx1 - bx0) // n
    for i in range(n):
        v = (i + 0.5) / n
        on = v <= val
        kit.heat_cell(d, bx0 + i * cw, by, cw - 3, 30,
                      (0.85 if on else 0.14) * (1.0 if snapped else 0.8), STEEL)
    cxp = int(bx0 + val * (bx1 - bx0))
    d.line([cxp, by - 16, cxp, by + 46], fill=steel(0.98), width=2)
    d.polygon([(cxp - 7, by - 16), (cxp + 7, by - 16), (cxp, by - 6)], fill=kit.mix(BLUE, 0.95))
    caption(d, (376, 400), "0.00", 14, 0.45)
    caption(d, (868, 400), "1.00", 14, 0.45)
    if snapped:
        caption(d, (846, 238), "stable", 18, 0.98, GRN)
        slab_text(d, (884, 430), "乖", 24, kit.blue(0.95), pad=6)
        if p < snap_t + 0.14:
            tint_frame(img, (60, 90, 160), 0.10)
    else:
        caption(d, (846, 238), "settling", 18, 0.5)


# ================================================================ S27
# 129.54-131.88  the same panel, a hand pushes the cursor over the line
S27_BOX = S26_BOX


def draw_s27(img, d, t, s):
    p = t - s.t0
    push = clamp01((p - 0.42) / 0.90)
    val = lerp(0.70, 0.96, _ease(push))
    over = clamp01((val - 0.705) / 0.10)              # crossing 0.70
    chaos = clamp01((p - 0.55) / 0.75) * clamp01(over * 1.4)
    seed = 9000 + int(t * 24)

    # everything that was exactly on the grid starts drifting apart again
    amp = 7.0 * chaos
    pts = []
    for gx, gy, dx, dy in _s26_ticks():
        wx = amp * math.sin((gy + t * 60) * 0.05)
        wy = amp * 0.7 * math.cos((gx + t * 50) * 0.04)
        vx = 5 + amp * 0.6 * math.sin(gx * 0.31)
        vy = amp * 0.5 * math.cos(gy * 0.27)
        for n in range(7):
            pts.append((gx + wx * n / 6.0 + vx * 0.5, gy + wy * n / 6.0 + vy * 0.4))
    d.point(pts, fill=steel(0.55 + 0.2 * chaos))

    if chaos > 0.05:
        sp = noise_tile(160, 90, 8, seed, "amber")
        kit.paste_clipped(img, kit.scale_alpha(sp, 0.05 + 0.22 * chaos), 0, 0, (0, 0, W, H))

    if chaos < 0.55:
        panel(d, S27_BOX, "temperature", 0.55 * (1 - chaos) + 0.2)
    else:
        jitter_box(d, S27_BOX, 0.72, 4 * chaos, 3 * chaos, seed, kit.ERR)
    x0, y0, x1, y1 = S27_BOX
    if chaos > 0.45:
        caption(d, (x0 + 22, y0 + 12), "unstable !!!", 20, 0.98, kit.ERR)
    else:
        caption(d, (x0 + 22, y0 + 12), "temperature", 16, 0.6)

    cjk_text(d, (x0 + 38, y0 + 46), "温度", 24, steel(0.85))
    caption(d, (x0 + 140, y0 + 36), "%.2f" % val, 34, 0.98)
    bx0, bx1, by = x0 + 50, x0 + 570, y0 + 124
    n = 26
    cw = (bx1 - bx0) // n
    for i in range(n):
        v = (i + 0.5) / n
        kit.heat_cell(d, bx0 + i * cw, by, cw - 3, 30,
                      0.85 if v <= val else 0.14, kit.ERR if chaos > 0.6 and v <= val else STEEL)
    cxp = int(bx0 + val * (bx1 - bx0))
    d.line([cxp, by - 16, cxp, by + 46], fill=steel(0.98), width=2)

    if over > 0:
        jitter_cjk(d, x0 + 560, y0 + 200, "胡说", 32,
                   kit.mix(kit.RED, 0.9), 3.0 * chaos, seed)
    else:
        slab_text(d, (x0 + 554, y0 + 202), "乖", 24, kit.blue(0.95), pad=6)

    if p > 0.30:
        hu = clamp01((p - 0.30) / 0.30)
        hx = int(lerp(1320, cxp + 34, _ease(hu)))
        if p < 1.62:
            hand(d, hx - 40, by - 62, 0.5, 0.85)
    if chaos > 0.02:
        tint_frame(img, PURP, 0.18 * chaos + 0.04)


# ================================================================ S28
# 131.88-133.82  the score panel (5/7): the needle jams, "answer too long"
def draw_s28(img, d, t, s):
    p = t - s.t0
    panel(d, (430, 140, 850, 560), "Q: love_score", 0.6)
    cjk_text(d, (470, 186), "你爱我几分", 24, steel(0.9))

    cx, cy, r = 640, 400, 120
    for i in range(37):
        a = math.pi - i * math.pi / 36.0
        x = cx + math.cos(a) * r
        y = cy - math.sin(a) * r
        major = i % 6 == 0
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=steel(0.75 if major else 0.35))
    ang = math.pi - (math.pi * 0.5) * _ease(clamp01(p / 1.24))
    if p > 1.24:
        ang += 0.012 * math.sin(t * 9.0)              # jammed, but alive
    d.line([cx, cy, cx + math.cos(ang) * (r - 14), cy - math.sin(ang) * (r - 14)],
           fill=steel(0.98), width=3)
    d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=steel(0.9))
    caption(d, (596, 250), "%.2f" % (0.5 * _ease(clamp01(p / 1.24))), 26, 0.9)

    msg = "answer too long"
    k = int((t - s.t0) * 6) % len(msg)
    for i, ch in enumerate(msg):
        d.text((470 + i * 16, 500), ch, font=mono(15),
               fill=kit.mix(kit.RED if i == k else STEEL, 0.95 if i == k else 0.55))
    cursor_block(d, 800, 500, t, 16, 7, 0.9)


# ================================================================ S29
# 133.82-137.86  VRAM bar (6/7): OOM, the top-up button that will not press
def _vram_bar(d, box, cells: int, freed: int, base_lv: float):
    x0, y0, x1, y1 = box
    gap = 3
    cw = max(2, (x1 - x0 - gap * (cells - 1)) // cells)
    for i in range(cells):
        x = x0 + i * (cw + gap)
        if i >= cells - freed:
            kit.heat_cell(d, x, y0, cw, y1 - y0, 0.05, STEEL)
        else:
            kit.heat_cell(d, x, y0, cw, y1 - y0, base_lv, STEEL)


def draw_s29(img, d, t, s):
    p = t - s.t0
    squeeze = _ease(clamp01(p / 0.62))
    collapse = _ease(clamp01((p - 3.58) / 0.30))
    x0 = int(lerp(lerp(430, 290, squeeze), 500, collapse))
    x1 = int(lerp(lerp(850, 990, squeeze), 790, collapse))
    y0 = int(lerp(lerp(140, 300, squeeze), 270, collapse))
    y1 = int(lerp(lerp(560, 380, squeeze), 412, collapse))
    panel(d, (x0, y0, x1, y1), "vram", 0.6 * (1 - 0.35 * collapse))

    if p < 0.62:
        cx, cy, r = 640, 400, 120
        lv = (1 - squeeze) * 0.8
        if lv > 0.05:
            for i in range(0, 37, 3):
                a = math.pi - i * math.pi / 36.0
                d.ellipse([cx + math.cos(a) * r - 2, cy - math.sin(a) * r - 2,
                           cx + math.cos(a) * r + 2, cy - math.sin(a) * r + 2], fill=steel(lv))

    freed = int(clamp01((t - 135.14) / 1.0 / 0.0555)) if t > 135.14 else 0
    freed = min(24, freed)
    bar_lv = 0.88 * (1 - collapse)
    if bar_lv > 0.06:
        _vram_bar(d, (x0 + 20, (y0 + y1) // 2 - 16, x1 - 20, (y0 + y1) // 2 + 18), 24, freed, bar_lv)
    if collapse < 0.5:
        caption(d, (x0 + 20, y0 - 30), "vram  %.1fG / 24.0G" % (24.0 * (1 - freed / 24.0)), 16, 0.72)
        if t > 135.14:
            cjk_text(d, (x0 + 20, y1 + 14), "显存", 18, steel(0.6))
    if 135.90 < t < 137.55 and collapse < 0.4:
        caption(d, (x1 - 150, y0 - 36), "OOM !!", 22, 0.55 + 0.45 * pulse(t, 0.62), kit.ERR)

    if 136.34 < t < 137.45:
        su = _ease(clamp01((t - 136.34) / 0.34))
        px0 = int(lerp(1290, 760, su))
        panel(d, (px0, 430, px0 + 390, 600), "charge", 0.62)
        caption(d, (px0 + 22, 452), "balance 0.00", 15, 0.55)
        btn = (px0 + 70, 512, px0 + 300, 570)
        shake = 4 * math.sin(t * 40) if 136.95 < t < 137.25 else 0
        btn = (btn[0] + shake, btn[1], btn[2] + shake, btn[3])
        dash_rect(d, btn, kit.mix(BLUE, 0.55), 9, 7)
        slab_text(d, (btn[0] + 30, btn[1] + 12), "+ 充值", 24, steel(0.95), pad=6)
        if t < 136.95:
            caption(d, (btn[0] + 236, btn[1] + 16), "_", 20, 0.9, BLUE)
        elif t < 137.42:
            d.line([btn[0] + 240, btn[1] + 14, btn[0] + 262, btn[1] + 36], fill=kit.mix(kit.RED, 0.9), width=2)
            d.line([btn[0] + 262, btn[1] + 14, btn[0] + 240, btn[1] + 36], fill=kit.mix(kit.RED, 0.9), width=2)
            caption(d, (px0 + 70, 578), "press failed", 15, 0.85, kit.ERR)

    if p > 3.58:
        cjk_text(d, (x0 + 26, (y0 + y1) // 2 - 14), "显存不太够用", 24, steel(0.95))


# ================================================================ S30
# 137.86-141.90  rice and code woven into a band, then the run
def _run_banner_x(t: float) -> float:
    if t < 141.42:
        return 1430.0
    if t <= 141.90:
        return lerp(1430.0, 700.0, _ease((t - 141.42) / 0.48))
    return 700.0 - 6.0 * (t - 141.90)


def _draw_band(d, off: float, prog: float, lv: float):
    step = 48
    k0 = int(off // step)
    for row in range(2):
        y = 278 + row * 46 - (18 if row else 0)
        for i in range(-1, W // step + 2):
            k = k0 + i + row
            x = i * step - (off % step)
            if x < -step or x > W:
                continue
            rng = random.Random(k * 31 + row)
            is_rice = rng.random() < (0.34 + 0.28 * prog)
            if is_rice:
                for a in range(3):
                    for b in range(3):
                        if a == 1 and b == 1:
                            continue
                        d.rectangle([x + 6 + a * 10, y + 6 + b * 10, x + 12 + a * 10, y + 12 + b * 10],
                                    fill=kit.mix(BLUE, lv * rng.uniform(0.55, 1.0)))
            else:
                ch = "{}( );"[k % 6]
                d.text((x + 12, y + 4), ch, font=mono_b(30), fill=steel(lv * 0.8))


def draw_s30(img, d, t, s):
    p = t - s.t0
    # continuity: the small box from S29 still holds the line she is singing
    if p < 1.05:
        fo = 1.0 - clamp01((p - 0.55) / 0.50)
        panel(d, (500, 270, 790, 412), "vram", 0.5 * fo + 0.08)
        slab_text(d, (526, 320), "显存不太够用", 24, steel(0.9 * fo + 0.1), pad=6)

    prog = clamp01(p / 3.6)
    speed = 140.0 + 1700.0 * _ease(clamp01((p - 3.56) / 0.34))
    off = 0.0
    if p < 3.56:
        off = p * 140.0
    else:
        off = 3.56 * 140.0 + (p - 3.56) * speed * 0.35 + 300.0 * (p - 3.56) ** 2
    slip = min(120.0, (speed - 140.0) * 0.05)
    for j, (dx, lv) in enumerate(((slip, 0.40), (slip * 0.45, 0.55), (0.0, 1.0))):
        _draw_band(d, off - dx, prog, lv * (0.75 if j < 2 else 1.0))

    if p > 3.48:
        sp = banner("LET ME RUN", rows=22, px=8, fg=steel(0.9), bg=BG, max_w=1200)
        clash = clamp01((p - 3.56) / 0.34)
        kit.paste_clipped(img, sp, int(_run_banner_x(t)), 250 + int(6 * math.sin(t * 40) * clash),
                          (0, 96, W, 610))
        if clash > 0.4:
            nz = noise_tile(120, 40, 8, 5000 + int(t * 24), "amber")
            kit.paste_clipped(img, kit.scale_alpha(nz, 0.3 * clash), 0, 96, (0, 96, W, 610))


# ================================================================ S31
# 141.90-145.58  the half banner is eaten by the dot field, one blue dot breathes
def draw_s31(img, d, t, s):
    p = t - s.t0
    eat = clamp01((p - 0.26) / 1.50)
    sp = banner("LET ME RUN", rows=22, px=8, fg=steel(0.9), bg=BG, max_w=1200)
    sp = sp.copy()                                     # banner_block is lru_cached
    if eat > 0:
        cols, rows = 116, 22
        rng = random.Random(8)
        m = Image.new("L", (cols, rows))
        m.putdata([0 if rng.random() < eat else 255 for _ in range(cols * rows)])
        m = m.resize(sp.size, Image.NEAREST)
        sp.putalpha(ImageChops.multiply(sp.getchannel("A"), m))
    sp = kit.scale_alpha(sp, 1.0 - 0.55 * clamp01((p - 2.6) / 1.2))
    kit.paste_clipped(img, sp, int(_run_banner_x(t)), 250, (0, 96, W, 610))

    if eat > 0.35:
        fade = clamp01((p - 1.30) / 1.40) * 0.46
        tint_frame(img, (0, 0, 0), fade)

    # the one blue dot left on screen: her heartbeat, with a soft halo
    for k, (dx, dy, lv) in enumerate(((10, 5, 0.10), (5, 2, 0.18), (0, 0, 1.0))):
        cursor_block(d, 626 - dx, 322 - dy, t, 30 + 2 * dx, 10 + 2 * dy, lv)
    if p > 3.24:
        wi = clamp01((p - 3.24) / 0.34)
        wipe(img, min(0.999, wi))
        cursor_block(d, 626, 322, t, 30, 10, 1.0)


SHOTS = {
    "S17": draw_s17, "S18": draw_s18, "S19": draw_s19, "S20": draw_s20,
    "S21": draw_s21, "S22": draw_s22, "S23": draw_s23, "S24": draw_s24,
    "S25": draw_s25, "S26": draw_s26, "S27": draw_s27, "S28": draw_s28,
    "S29": draw_s29, "S30": draw_s30, "S31": draw_s31,
}
