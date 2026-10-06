"""Sticker pack support: DSH meme packs as a PV asset.

Packs live under ~/.dsh/meme-packs/<id>/ as memes/<tag>/<file>, with an index.db
holding a caption per sticker. Two are installed:

    whale-girl-emoji   91 张  license: noncommercial-fan  维护者 Luocheng114
    deepseek-chan     128 张  license: 未声明

`whale-girl-emoji` is the one this film uses: it declares a licence, and its
stickers depict the very actions the lyrics describe (端着白饭干饭、上班摸鱼、
趴在电脑前加班、拎包冲出办公室). `deepseek-chan` has richer meme-scene captions
but ships no licence at all, which cannot be cleared for a published film.

Stickers are complete cards -- full colour, own background, often with baked-in
text -- so the treatment question is how much of that to keep.

    card = sticker("daily", "1790141445954_633", 360, 400, style="duotone")
    img.paste(card, (x, y), card)

Styles, because a full-colour sticker inside a monochrome TUI film is a choice
that has to be seen to be judged:
    raw       as drawn -- warm, but it fights the palette
    duotone   background mapped to the film's black, the rest to one colour
    ink       duotone plus a hard posterise, which pulls it toward the TUI look
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from .. import config as _cfg  # noqa: E402

PACK_ID = _cfg.STICKER_PACK
PACKS = Path(_cfg.MEME_PACKS)
_CACHE: dict = {}


def pack_dir(pack_id: str | None = None) -> Path:
    return PACKS / (pack_id or PACK_ID) / "memes"


def path(tag: str, name: str, pack_id: str | None = None) -> Path:
    d = pack_dir(pack_id) / tag
    for ext in (".webp", ".png", ".jpg"):
        p = d / f"{name}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"{d}/{name}.webp|png|jpg")


def load(tag: str, name: str, pack_id: str | None = None) -> Image.Image:
    key = ("raw", pack_id or PACK_ID, tag, name)
    if key not in _CACHE:
        _CACHE[key] = Image.open(path(tag, name, pack_id)).convert("RGB")
    return _CACHE[key]


def _duotone(im: Image.Image, col, lo: float = 0.0, hi: float = 1.0) -> Image.Image:
    g = ImageOps.grayscale(im)
    g = ImageOps.autocontrast(g, cutoff=1)
    # the sticker's own background is usually the lightest thing in the frame, so
    # pull it down to the film's black and lift the drawing into `col`
    g = g.point(lambda v: int(255 * max(0.0, min(1.0, (v / 255.0 - lo) / max(1e-6, hi - lo)))))
    return ImageOps.colorize(g, black=(6, 8, 14), white=col)


def _sentinel_mask(im: Image.Image, thr: int = 38) -> Image.Image:
    """L mask: 255 where the sticker's own artwork is, 0 on the background.

    Flood fills inward from the border rather than thresholding white, because a
    flat background is one connected region: thresholding would also knock out
    the white apron, the eye highlights and the teeth, and those are the drawing.

    Seeds from EVERY border pixel, not just the pale ones -- about a third of
    this pack sits on a dark card, and a white-only seed leaves those as a dark
    rectangle stuck to the character. Each fill grows from its own starting
    colour, so whatever the card is, it goes.

    Baked-in lettering survives on purpose -- the caption is the joke.
    """
    sc = 300 / max(im.size)
    small = im.resize((max(8, int(im.width * sc)), max(8, int(im.height * sc))),
                      Image.LANCZOS)
    SENT = (255, 0, 255)
    work = small.copy()
    w, h = work.size

    seeds = ([(x, 0) for x in range(0, w, 5)] + [(x, h - 1) for x in range(0, w, 5)]
             + [(0, y) for y in range(0, h, 5)] + [(w - 1, y) for y in range(0, h, 5)])
    for s in seeds:
        if work.getpixel(s) == SENT:
            continue
        try:
            ImageDraw.floodfill(work, s, SENT, thresh=thr)
        except Exception:
            pass

    mask = Image.new("L", (w, h), 255)
    mp, wp = mask.load(), work.load()
    for y in range(h):
        for x in range(w):
            if wp[x, y] == SENT:
                mp[x, y] = 0
    # a guard: if the fill swallowed almost everything, the "background" was
    # really the artwork and the result would be an empty rectangle
    if mask.histogram()[0] > 0.92 * w * h:
        mask = Image.new("L", (w, h), 255)
    mask = mask.filter(ImageFilter.MedianFilter(3)).resize(im.size, Image.LANCZOS)
    return mask.point(lambda v: 255 if v > 110 else 0)


def figure(tag: str, name: str, max_w: int, max_h: int, pack_id: str | None = None,
           thr: int = 38, pad: int = 0) -> Image.Image:
    """Just the character, background gone -- an RGBA sprite to paste over a scene."""
    key = ("fig", pack_id or PACK_ID, tag, name, max_w, max_h, thr, pad)
    if key in _CACHE:
        return _CACHE[key]
    im = load(tag, name, pack_id)
    m = _sentinel_mask(im, thr)
    out = im.convert("RGBA")
    out.putalpha(m)
    bbox = out.getchannel("A").getbbox()
    if bbox:
        x0, y0, x1, y1 = bbox
        out = out.crop((max(0, x0 - pad), max(0, y0 - pad),
                        min(out.width, x1 + pad), min(out.height, y1 + pad)))
    out.thumbnail((max_w, max_h), Image.LANCZOS)
    _CACHE[key] = out
    return out


def card(tag: str, name: str, w: int, h: int, style: str = "duotone",
         col=(196, 212, 255), ink_levels: int = 6, pack_id: str | None = None) -> Image.Image:
    key = ("card", pack_id or PACK_ID, tag, name, w, h, style, col, ink_levels)
    if key in _CACHE:
        return _CACHE[key]
    im = load(tag, name, pack_id)
    im.thumbnail((w, h), Image.LANCZOS)

    if style == "raw":
        out = im
    elif style == "duotone":
        out = _duotone(im, col)
    elif style == "ink":
        d = _duotone(im, col)
        q = max(2, ink_levels)
        out = d.point(lambda v: int(round(v / 255 * (q - 1)) * 255 / (q - 1)))
    else:
        raise ValueError(style)

    _CACHE[key] = out
    return out


def framed(img: Image.Image, title: str = "her.sticker", level: float = 0.5,
           pad: int = 10, active: bool = True):
    """The sticker inside a TUI panel, sized to fit -- how a sticker would appear
    if she pasted one into the terminal."""
    from pvlib.kit import panel, STEEL
    im = img.convert("RGB")
    W, H = im.width + pad * 2, im.height + pad * 2 + 22
    out = Image.new("RGB", (W, H), (4, 7, 15))
    d = ImageDraw.Draw(out)
    panel(d, (0, 0, W - 1, H - 1), title=title, level=level, color=STEEL, active=active)
    out.paste(im, (pad, pad + 18))
    return out
