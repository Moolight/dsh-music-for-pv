"""Work out where each sticker can sit without covering the scene.

The sticker track is an overlay, so on a busy shot it lands on top of a panel or
on her. Moving them by hand is 21 guesses that go stale the moment a shot
changes, so instead this measures: for every cue, render the scene alone at
several moments, score every candidate slot by how much picture it would hide,
and keep the emptiest.

Writes out/sticker_place.json, which render.py reads if it is there and falls back
to the cue's own x/y otherwise.

    python place_stickers.py            rewrite the placement table
    python place_stickers.py --report   also print a per-cue table
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import render  # noqa: E402
from pvlib.assets import stickers as stk  # noqa: E402

OUT = PROJECT / "out" / "sticker_place.json"
SAFE_TOP = 46
SAFE_BOTTOM = 612          # the lyric band starts at 620
BUDGET = 400               # summed-luminance per sample we are willing to hide
SCALES = (1.0, 0.84, 0.68)  # shrink until it fits, rather than blot out the shot


def slots(w: int, h: int):
    """Candidate top-left corners, in preference order.

    Over a sparse scene most slots score zero, so the tie-break is what decides
    the layout -- picking the first empty slot puts every sticker in the top-left
    corner. Candidates are therefore ordered right-to-left, top-to-bottom: the
    right of frame is where shots least often put the thing being sung about,
    and staying high keeps clear of the lyric band.
    """
    xs = [1280 - 24 - w, 1040, 880, 720, 560, 400, 240, 24]
    ys = [SAFE_TOP, SAFE_TOP + 130, SAFE_TOP + 260, SAFE_BOTTOM - h]
    out = []
    for y in sorted(set(ys)):
        if not (SAFE_TOP <= y <= SAFE_BOTTOM - h):
            continue
        for x in xs:
            if 0 <= x <= 1280 - w:
                out.append((x, y))
    return out


def scene_ink(t: float) -> Image.Image:
    """The frame as it would be without any sticker: a coarse ink map."""
    img = Image.new("RGB", (render.W, render.H), render.kit.BG)
    img.paste(render.kit.dot_field(render.W, render.H - 16), (0, 0))
    render.scenes.draw(img, t)
    render.draw_band(img, t)
    small = img.convert("L").resize((render.W // 8, render.H // 8), Image.BOX)
    return small


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()

    place: dict[str, list[int]] = {}
    rows = []
    for t0, t1, tag, name, x, y, w in render.STICKERS:
        key = f"{tag}/{name}"
        try:
            ts = [t0 + (t1 - t0) * f for f in (0.18, 0.45, 0.78)]
            inks = [scene_ink(t) for t in ts]
        except Exception as e:
            print(f"  {key}: {e}")
            place[key] = [x, y, w]
            continue

        chosen = None          # first size that fits the budget
        fallback = None        # otherwise, the size that hides the least
        for scale in SCALES:
            sw = int(w * scale)
            try:
                card = stk.figure(tag, name, sw, int(sw * 1.35))
            except Exception as e:
                print(f"  {key}: {e}")
                break
            cw, ch = card.size
            cands = slots(cw, ch)
            if not cands:
                break
            best, best_cost = cands[0], None
            for cx, cy in cands:                  # already in preference order
                box = (cx // 8, cy // 8, (cx + cw) // 8, (cy + ch) // 8)
                cost = sum(max(0, v - 14) for ink in inks for v in ink.crop(box).getdata())
                # strictly less wins, so ties keep the earlier (preferred) slot
                if best_cost is None or cost < best_cost:
                    best, best_cost = (cx, cy), cost
            per = (best_cost or 0) / max(1, len(inks))
            rec = (best[0], best[1], sw, best_cost or 0, cw, ch, scale)
            if fallback is None or per < fallback[3] / max(1, len(inks)):
                fallback = rec
            if per < BUDGET:
                chosen = rec
                break
        if chosen is None:
            chosen = fallback

        if chosen is None:
            place[key] = [x, y, w]
            continue
        px, py, pw, cost, cw, ch, scale = chosen
        place[key] = [px, py, pw]
        rows.append((t0, tag, name, (x, y), (px, py), pw, int(cost),
                     round(100.0 * cost / max(1, (cw // 8) * (ch // 8) * len(inks)), 1),
                     scale, cw, ch))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(place, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(place)} cues -> {OUT}")
    if a.report:
        print(f"\n{'t0':>7} {'cue':<26} {'old':>12} {'new':>12} {'w':>4} {'scale':>5} "
              f"{'ink':>7} {'%':>6}  size")
        for t0, tag, name, old, new, pw, cost, pct, scale, cw, ch in rows:
            moved = "  " if tuple(old) == tuple(new) else "->"
            print(f"{t0:7.2f} {tag + '/' + name.split('_')[-1]:<26} {str(old):>12} "
                  f"{moved}{str(new):>12} {pw:4d} {scale:5.2f} {cost:7d} {pct:6.1f}  {cw}x{ch}")


if __name__ == "__main__":
    main()
