"""Shared toolkit and shot interface.

Every shot module imports from here and nothing else of ours, so four of them can
be written side by side without touching a shared file.

A shot is a function:

    def draw_s01(img: Image.Image, d: ImageDraw.ImageDraw, t: float, s: Shot) -> None

`img` already has the dot field painted; draw on top of it. `t` is the absolute
song time in seconds. Everything must be a pure function of `t` -- frames get
rendered out of order and in parallel chunks -- so never keep state across calls
except caches keyed by arguments.

Conventions the design document fixes (SHOTS.md sections 4.3 and 4.4):
  * brand blue #4D6BFE (`kit.BLUE_MID` / `kit.blue`) belongs to HER only -- her
    body, and things she makes: rice, the heartbeat cursor, her name tag.
    System things (cache, token counter, panel frames, racks, weight matrix) stay
    cold steel (`kit.UI` / `kit.amb`).
  * at most ONE panel may be "active" at a time; any other panel sits at 20%.
  * a clear sweep (`wipe`) every 20-30 s.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

# The palette is chosen at import time by tuikit, so this must be set before it is
# imported -- and it belongs here rather than in pv.py, so that importing a shot
# module on its own for a test still gets the deep-sea look.
os.environ.setdefault("TUI_PALETTE", "deepsea")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from . import config  # noqa: E402

# The toolkit is vendored under pvlib/vendor/ (MIT, MisakaZentai) so this project
# runs on its own. Point PV_TUI at a clone of the upstream repository to use that
# copy instead -- useful when working on the toolkit itself.
TUI = Path(config.TUI) if config.TUI else None
if TUI and TUI.exists():
    if str(TUI) not in sys.path:
        sys.path.insert(0, str(TUI))
    import tuikit as kit  # noqa: E402
else:
    from pvlib.vendor import tuikit as kit  # noqa: E402

# Re-export the whole toolkit, plus the PIL pieces the shots reach for. Shot
# modules are written against tuikit's documented API, so anything missing here
# turns into a NameError at import time that takes the entire film down -- the
# cheapest fix is to expose everything and let the names resolve.
#
# This is `from tuikit import *` spelled out, because the vendored copy is not a
# top-level module. Names defined further down this file win, as they would with
# a star-import.
globals().update({n: getattr(kit, n) for n in dir(kit) if not n.startswith("_")})
from PIL import ImageChops  # noqa: E402,F401  (some shots blend directly)

# The default vignette crushes the bottom of the frame: measured ink for an 18 px
# line at y=690 drops from 2269 to 154, i.e. effectively black. LYRIC_LIFT keeps
# the vignette off the lyric band, restoring it to 1669.
kit.LYRIC_LIFT[0] = True

W, H = kit.W, kit.H
FPS = 24
BEAT = 0.606          # quarter note at 99 BPM, from the score's Q:1/4=99
HEART = 2 * BEAT      # the 1.21 s breathing period used throughout the film

# Post-processing: measured on CJK, these are the ceilings for legible Chinese.
# The trail is a "lighter" blend, i.e. the previous frame double-exposes onto this
# one, and at 0.42/0.35 an 18 px line is unreadable; bloom is additive and lifts
# the black floor into fog. 0.12/0.10 keeps both effects without eating strokes.
TRAIL, BLOOM = 0.12, 0.10

# tuikit's colour names, re-exported under both spellings: shot modules naturally
# reach for BLUE_MID / BLUE_TEXT, and having them missing is a NameError at import
# time that breaks the whole film, not just one shot.
BG = kit.BG
UI = kit.UI
ERR = kit.ERR
ANOM = kit.ANOM
BLUE_LO = kit.BLUE_LO
BLUE_MID = kit.BLUE_MID
BLUE_HI = kit.BLUE_HI
BLUE_TEXT = kit.BLUE_TEXT

BLUE = kit.BLUE_MID          # "her" colour, the brand blue #4D6BFE
STEEL = kit.UI               # the system's colour: panels, counters, matrices
DIM = (64, 70, 90)

# Font size floors, from the same probe (msyh.ttc at 1280x720):
#   24 px  body lyrics -- comfortable, use this for the lyric band
#   32 px  titles / big Chinese
#   18 px  lower bound for anything the viewer must read
#   14 px  short annotations only; strokes are 1 px and dense hanzi start to merge
SZ_BODY, SZ_TITLE, SZ_MIN, SZ_TINY = 24, 32, 18, 14


# ---------------------------------------------------------------- timeline

def _load():
    tl = json.loads((config.OUT / "timeline.json").read_text(encoding="utf8"))
    shots = json.loads((config.OUT / "shots.json").read_text(encoding="utf8"))
    return tl, shots


TL, SHOT_ROWS = _load()
LINES = TL["lines"]
DURATION = float(TL["duration"])
BY_ID = {r["id"]: r for r in SHOT_ROWS}


@dataclass
class Shot:
    id: str
    t0: float
    t1: float
    idx: list                 # 1-based lyric line numbers this shot covers
    lines: list               # the corresponding timeline entries

    @property
    def dur(self) -> float:
        return self.t1 - self.t0

    def u(self, t: float) -> float:
        """Progress through the shot, 0..1."""
        return min(1.0, max(0.0, (t - self.t0) / max(1e-6, self.dur)))

    def since(self, t: float, at: float) -> float:
        """Seconds since absolute time `at` (negative before it)."""
        return t - at

    def line_at(self, t: float) -> dict | None:
        """The timeline line being sung at `t` within this shot (or None)."""
        cur = None
        for ln in self.lines:
            if ln["t"] <= t:
                cur = ln
            else:
                break
        return cur

    def line(self, n: int) -> dict:
        """The n-th covered line (1-based, matching SHOTS.md)."""
        return LINES[n - 1]


def shot_at(t: float) -> Shot | None:
    for r in SHOT_ROWS:
        if r["t0"] <= t < r["t1"]:
            return Shot(r["id"], r["t0"], r["t1"], r["lines"],
                        [LINES[i - 1] for i in r["lines"]])
    return None


# ---------------------------------------------------------------- animation

def clamp01(v: float) -> float:
    return 0.0 if v < 0 else (1.0 if v > 1 else v)


def fade_in(u: float, k: float = 0.15) -> float:
    return clamp01(u / k) if k > 0 else 1.0


def fade_out(u: float, k: float = 0.15) -> float:
    return clamp01((1.0 - u) / k) if k > 0 else 1.0


def pulse(t: float, period: float = HEART, lo: float = 0.0, hi: float = 1.0) -> float:
    """Breathing value in [lo, hi] with the film's 1.21 s period."""
    k = 0.5 - 0.5 * math.cos(2 * math.pi * t / period)
    return lo + (hi - lo) * k


def heartbeat(t: float, period: float = HEART) -> float:
    """Sharper than pulse: a quick thump then a slow recovery (a real heartbeat)."""
    u = (t % period) / period
    return clamp01(math.exp(-9 * u) * 1.0) if u < 0.35 else 0.0


def overshoot(u: float, k: float = 1.7) -> float:
    """Ease-out with one frame of overshoot, used for landing highlights."""
    u = clamp01(u)
    return 1 - (1 - u) ** 3 * math.cos(k * math.pi * u * 0.5) if u < 1 else 1.0


def lerp(a: float, b: float, u: float) -> float:
    return a + (b - a) * clamp01(u)


# ---------------------------------------------------------------- text

_CJK_CACHE: dict = {}


def cjk(size: int) -> ImageFont.FreeTypeFont:
    if size not in _CJK_CACHE:
        _CJK_CACHE[size] = ImageFont.truetype(kit.F_CJK, size)
    return _CJK_CACHE[size]


def cjk_w(s: str, size: int) -> float:
    return cjk(size).getlength(s)


def cjk_text(d: ImageDraw.ImageDraw, xy, s: str, size: int, fill, anchor=None) -> None:
    d.text(xy, s, font=cjk(size), fill=fill, anchor=anchor)


def cjk_center(d: ImageDraw.ImageDraw, cx: float, y: float, s: str, size: int, fill) -> None:
    d.text((cx - cjk_w(s, size) / 2, y), s, font=cjk(size), fill=fill)


def mono(size: int) -> ImageFont.FreeTypeFont:
    return kit.font(kit.F_MONO, size)


def mono_b(size: int) -> ImageFont.FreeTypeFont:
    return kit.font(kit.F_MONO_B, size)


def caption(d: ImageDraw.ImageDraw, xy, s: str, size: int = 15, level: float = 0.55,
            color=None) -> None:
    """Small terminal-style label, the workhorse for annotating panels.

    ASCII only: the monospace faces here have no hanzi, so Chinese through this
    path renders as tofu boxes. Use `cjk_text` for Chinese.
    """
    d.text(xy, s, font=mono(size), fill=kit.mix(color or STEEL, level))


def slab_text(d: ImageDraw.ImageDraw, xy, s: str, size: int, fill, pad: int = 6) -> None:
    """Chinese over a sprite or a busy matrix is swallowed by the bright pixels
    underneath; an opaque background slab behind the glyphs restores it fully.
    Use this whenever text sits on top of anything other than empty background.
    """
    x, y = xy
    d.rectangle([x - pad, y - pad // 2, x + cjk_w(s, size) + pad, y + size + pad // 2],
                fill=kit.BG)
    d.text((x, y), s, font=cjk(size), fill=fill)


def dec(d: ImageDraw.ImageDraw, xy, s: str, t: float, at: float, size: int = 15,
        level: float = 0.75, rate: float = 22.0, color=None) -> None:
    """Typewriter with glyph flicker, keyed to absolute time `at`."""
    rng = random.Random(hash((s, int(at * 1000))) & 0xFFFFFFFF)
    d.text(xy, kit.decode(s, t - at, rng, rate=rate), font=mono(size),
           fill=kit.mix(color or STEEL, level))


# ---------------------------------------------------------------- widgets

def panel(d: ImageDraw.ImageDraw, box, title: str = "", level: float = 0.55,
          color=None, active: bool = True) -> None:
    """A panel frame. Inactive panels sit dim, per the one-active-panel rule.

    The title goes through a monospace face with no hanzi, so it must be ASCII;
    draw any Chinese label yourself inside the panel with `cjk_text`.
    """
    lv = level if active else level * 0.36
    kit.box(d, box[0], box[1], box[2], box[3], title=title, level=lv,
            color=color or STEEL)


def wipe(img: Image.Image, u: float, color=None) -> None:
    """Clear-sweep: a band that erases the frame from the middle outwards."""
    if u <= 0 or u >= 1:
        return
    d = ImageDraw.Draw(img)
    half = u * (W / 2 + 80)
    cx = W / 2
    for sgn in (-1, 1):
        x0 = cx + sgn * max(0.0, half - 80)
        x1 = cx + sgn * half
        d.rectangle([min(x0, x1), 0, max(x0, x1), H], fill=kit.BG)
    edge = kit.mix(color or STEEL, 0.5)
    d.line([cx - half, 0, cx - half, H], fill=edge)
    d.line([cx + half, 0, cx + half, H], fill=edge)


def bars(d: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, n: int, vals,
         gap: int = 2, color=None) -> None:
    """A row of vertical level bars -- used for counters, tokens, meters."""
    bw = max(1, (w - gap * (n - 1)) // n)
    for i, v in enumerate(vals[:n]):
        bh = int(h * clamp01(v))
        d.rectangle([x + i * (bw + gap), y + h - bh, x + i * (bw + gap) + bw, y + h],
                    fill=kit.mix(color or STEEL, 0.2 + 0.8 * clamp01(v)))


def sprite(expr: str, crop: str, max_w: int, max_h: int, px: int = 4, tint: str = "blue"):
    return kit.halfblock(expr, crop, max_w, max_h, px=px, tint=tint)


def glyph(expr: str, crop: str, cols: int, size: int = 10, tint: str = "blue",
          scramble: float = 0.0, reveal: float = 1.0, t: float = 0.0):
    rng = random.Random(1234)
    return kit.glyph_sprite(expr, crop, cols, int(cols * 0.898 * 0.5), size=size,
                            scramble=scramble, rng=rng, tint=tint, reveal=reveal)


def banner(text: str, rows: int = 18, px: int = 8, fg=None, bg=None, max_w: int = 1100):
    """Blocky banner letters. LATIN ONLY -- Anton has no hanzi, and feeding it
    Chinese produces garbled glyphs, so never call this with Chinese."""
    return kit.banner_block(text, rows, px, fg or STEEL, bg or kit.BG, max_w=max_w)


def field():
    """The background dot grid. dot_field returns (w, h + step), so pass H - 16
    or the grid runs 16 px past the bottom of the canvas."""
    return kit.dot_field(W, H - 16)
