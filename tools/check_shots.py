"""Render one frame from every shot and tile them, as a whole-film check.

Rendering the full film to find out that shot S34 crashes is expensive; this
walks all 57 shots at their midpoint first and shows the result as one sheet, so
broken or empty shots are obvious before committing to a long render.

    python check_shots.py                 every shot, midpoint
    python check_shots.py --at 0.25 0.75  two frames per shot instead
    python check_shots.py --only S32 S33
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

import render  # noqa: E402

COLS, TW, TH = 5, 256, 144


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", nargs="*", type=float, default=[0.5],
                    help="fraction(s) through each shot to sample")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--out", default="out/shot_check.png")
    a = ap.parse_args()

    rows = json.loads((PROJECT / "out" / "shots.json").read_text(encoding="utf8"))
    if a.only:
        rows = [r for r in rows if r["id"] in set(a.only)]

    tiles, labels, bad = [], [], []
    for r in rows:
        for frac in a.at:
            t = r["t0"] + (r["t1"] - r["t0"]) * frac
            try:
                im = render.render_frame(t, None)
            except Exception as e:
                bad.append((r["id"], f"{type(e).__name__}: {e}"))
                im = Image.new("RGB", (render.W, render.H), (60, 0, 0))
            tiles.append(im.resize((TW, TH), Image.LANCZOS))
            labels.append(f"{r['id']} {t:.1f}s")

    rowsn = (len(tiles) + COLS - 1) // COLS
    canvas = Image.new("RGB", (TW * COLS, TH * rowsn), (0, 0, 0))
    d = ImageDraw.Draw(canvas)
    for i, im in enumerate(tiles):
        x, y = (i % COLS) * TW, (i // COLS) * TH
        canvas.paste(im, (x, y))
        d.rectangle([x, y, x + TW - 1, y + TH - 1], outline=(40, 44, 58))
        d.text((x + 4, y + 3), labels[i], fill=(255, 210, 120))
    out = PROJECT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"{len(tiles)} frames from {len(rows)} shots -> {out} ({canvas.width}x{canvas.height})")
    if bad:
        print(f"\n{len(bad)} shot(s) RAISED:")
        for sid, msg in bad:
            print(f"  {sid}: {msg[:150]}")
    else:
        print("all shots rendered without raising")


if __name__ == "__main__":
    main()
