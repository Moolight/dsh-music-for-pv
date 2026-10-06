"""The DeepSeek whale mark, as a PV asset.

The official logo is a black whale on a light rounded square, which makes it easy
to turn into a mask: threshold the luminance and the shape falls out, with the
eye and the inner fin left as holes. Two flavours are offered -- a filled
silhouette for the "real whale" in the hallucination, and the outline for when
the film wants a technical drawing of her.

    sp = whale(420, 300)                 # filled, brand blue
    sp = whale(600, 420, kind="edge")    # outline only
    img.paste(sp, (x, y), sp)
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps

# the shipped copy of the mark lives at the project root, not inside the package
ASSETS = Path(__file__).resolve().parents[2] / "assets"
SRC = ASSETS / "dsh-logo.png"

_CACHE: dict = {}


def _mask() -> Image.Image:
    """Mask of the whale alone, cropped to its bounding box.

    Neither channel works on its own. The file is a pale rounded plate drawn at
    full alpha with a black whale on top of it, plus a soft shadow at partial
    alpha around the plate -- so alpha alone selects the whole square, and
    luminance alone selects the square plus the shadow. Intersecting them
    (opaque AND dark) leaves just the whale, with the eye and the inner fin kept
    as holes because those show the pale plate through.
    """
    key = ("mask",)
    if key in _CACHE:
        return _CACHE[key]

    im = Image.open(SRC).convert("RGBA")
    opaque = im.getchannel("A").point(lambda v: 255 if v > 250 else 0)
    dark = ImageOps.grayscale(im.convert("RGB")).point(lambda v: 255 if v < 110 else 0)
    m = ImageChops.multiply(opaque, dark)
    bbox = m.getbbox()
    if bbox:
        m = m.crop(bbox)
    _CACHE[key] = m
    return m


def whale(w: int, h: int, tint=(77, 107, 254), kind: str = "solid",
          level: float = 1.0, keep_holes: bool = True) -> Image.Image:
    """The mark at or under w x h, as RGBA in `tint`."""
    key = ("whale", w, h, tint, kind, round(level, 3), keep_holes)
    if key in _CACHE:
        return _CACHE[key]

    m = _mask().copy()
    m.thumbnail((w, h), Image.LANCZOS)

    if kind == "solid":
        a = m
    elif kind == "edge":
        e = m.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
        a = e.point(lambda v: min(255, int(v * 1.8)))
    elif kind == "soft":
        a = m.filter(ImageFilter.GaussianBlur(2)).point(lambda v: min(255, int(v * 1.3)))
    else:
        raise ValueError(kind)

    if not keep_holes:
        # fill the eye and the inner fin so it reads as one shape at small sizes
        a = a.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))

    a = a.point(lambda v: int(v * level))
    out = Image.new("RGBA", a.size, tint + (0,))
    out.putalpha(a)
    _CACHE[key] = out
    return out


def aspect() -> float:
    m = _mask()
    return m.height / m.width
