"""Draw title and credit cards.

Engine, not content: this renders whatever spec `content/credits.py` hands it, in
the film's own visual language (deep-sea palette, a panel frame, scanlines and
vignette). Cards come out as PNG sequences the same shape as the film frames, so
`encode.py` can concatenate them without touching the film itself.

The film has no empty lead-in -- the vocal starts at 0.00 -- so the head card is
prepended and the song delayed to match; the tail cards go after the last line.

    python cards.py head out/cards_head
    python cards.py tail out/cards_tail
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))

from content import credits  # noqa: E402
from pvlib import kit as sk  # noqa: E402

W, H, FPS = sk.W, sk.H, sk.FPS
F_CJK = "C:/Windows/Fonts/msyh.ttc"
F_CJK_B = "C:/Windows/Fonts/msyhbd.ttc"
F_MONO = "C:/Windows/Fonts/consola.ttf"

LBL_X, VAL_X = 130, 452      # a real two-column grid: Chinese is not monospaced
HEAD_DUR, TAIL_DUR = credits.HEAD_DUR, credits.TAIL_DUR


def _f(path: str, size: int):
    return ImageFont.truetype(path, size)


def card_image(spec) -> Image.Image:
    title, lines = spec
    img = Image.new("RGB", (W, H), sk.BG)
    img.paste(sk.field(), (0, 0))
    d = ImageDraw.Draw(img)
    sk.panel(d, (86, 74, W - 86, H - 74), title="credits", level=0.42)

    f_t = _f(F_CJK_B, 46)
    f_h = _f(F_CJK_B, 32)
    f_b = _f(F_CJK, 20)
    f_n = _f(F_CJK, 17)

    y = 114
    if title:
        d.text((LBL_X - 2, y), title, font=f_t, fill=sk.BLUE_TEXT)
        y += 76          # clear the descenders: at 46 px the rule can touch them
        d.line([LBL_X - 2, y, W - LBL_X + 2, y], fill=sk.kit.amb(0.28))
        y += 30

    for kind, a, b in lines:
        if kind == "g":
            y += 13
        elif kind == "h":
            d.text((LBL_X, y), a, font=f_h, fill=sk.UI)
            y += 48
        elif kind == "n":
            d.text((LBL_X, y), a, font=f_n, fill=sk.kit.amb(0.44))
            y += 26
        elif kind == "kv":
            if a:
                d.text((LBL_X, y), a, font=f_b, fill=sk.kit.amb(0.62))
            d.text((VAL_X, y), b, font=f_b, fill=sk.mix(sk.UI, 0.88))
            y += 31
        else:
            d.text((LBL_X, y), a, font=f_b, fill=sk.mix(sk.UI, 0.88))
            y += 31

    # scanlines and vignette only: the film's trail would double-expose the text
    img = img.convert("RGBA")
    img.alpha_composite(sk.scanlines())
    img.alpha_composite(sk.vignette(False))
    return img.convert("RGB")


def write_cards(spec, dur: float, outdir: Path, offset: int = 0) -> int:
    """Write one card as `dur` frames, numbered from `offset` so several cards can
    share one directory and be handed to ffmpeg as a single sequence."""
    outdir.mkdir(parents=True, exist_ok=True)
    base = card_image(spec)
    black = Image.new("RGB", (W, H), (0, 0, 0))
    n = int(round(dur * FPS))
    for i in range(n):
        t = i / FPS
        a = max(0.0, min(1.0, t / 0.5, (dur - t) / 0.5))   # fade in and out
        Image.blend(black, base, a).save(outdir / f"f_{offset + i:06d}.png")
    return n


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    which, out = sys.argv[1], Path(sys.argv[2]).resolve()
    if which == "head":
        print(f"head: {write_cards(credits.HEAD, HEAD_DUR, out)} frames "
              f"({HEAD_DUR}s) -> {out}")
    elif which == "tail":
        total, off = 0, 0
        for spec in credits.TAIL:
            off += write_cards(spec, TAIL_DUR, out, off)
            total += int(round(TAIL_DUR * FPS))
        print(f"tail: {total} frames ({len(credits.TAIL) * TAIL_DUR}s) -> {out}")
    else:
        sys.exit("first argument must be head or tail")


if __name__ == "__main__":
    main()
