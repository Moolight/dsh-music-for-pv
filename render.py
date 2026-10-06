"""Render the film, frame by frame.

This module is the wiring, not the film. It stacks the layers in order and hands
each one the tables it needs; what is actually drawn lives in `content/`, and how
each layer draws lives in `pvlib/`.

    background  pvlib.kit.dot_field
    scene       pvlib.scenes  ->  content/acts/act*.py
    overlays    pvlib.overlays.StickerTrack / RiceMeter  (+ content cues)
    band        pvlib.band.LyricBand
    post        pvlib.kit.post  (bloom, afterimage, scanlines, vignette)

Every frame is a pure function of song time `t` at 24 fps on 1280x720. The one
exception is the afterimage in `post`, which needs the previous frame -- so a
worker renders a contiguous run and keeps its own history, and `--workers` splits
the timeline into contiguous chunks rather than striding it.

    python render.py all [--workers N]        the whole song -> out/frames
    python render.py strip 60 78              a short window, for review
    python render.py range 158.2 164.3        re-render part of an existing set
    python render.py sheet out/review         contact sheet from a frame directory
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))

from pvlib import config, scenes  # noqa: E402
from pvlib.band import LyricBand  # noqa: E402
from pvlib.kit import BLOOM, TRAIL, kit, shot_at  # noqa: E402
from pvlib.overlays import RiceMeter, StickerTrack, load_placement  # noqa: E402

FPS = 24
W, H = kit.W, kit.H
DEBUG = os.environ.get("PV_DEBUG") == "1"
TIMELINE = config.OUT / "timeline.json"


# ---------------------------------------------------------------- the layers
def _timeline() -> dict:
    return json.loads(TIMELINE.read_text(encoding="utf8"))


_TL: dict | None = None


def _layers() -> tuple:
    """Build the overlay/band layer objects once, from this film's content."""
    global _TL
    if _TL is None:
        _TL = _timeline()
        from content import cues, rice

        _layers.band = LyricBand(_TL["lines"], decode_lines=cues.DECODE_LINES,
                                 no_lyric=cues.NO_LYRIC,
                                 no_lyric_head=cues.NO_LYRIC_HEAD, debug=DEBUG)
        _layers.stickers = StickerTrack(
            cues.STICKERS,
            place=load_placement(config.OUT / "sticker_place.json"),
            alpha=cues.STICKER_ALPHA,
            pack=config.STICKER_PACK)
        _layers.rice = RiceMeter(rice)
    return _TL, _layers.band, _layers.stickers, _layers.rice


def render_frame(t: float, prev: Image.Image | None) -> Image.Image:
    tl, band, stickers, rice = _layers()
    img = Image.new("RGB", (W, H), kit.BG)
    img.paste(kit.dot_field(W, H - 16), (0, 0))   # dot_field returns h + step
    scenes.draw(img, t)
    stickers.draw(img, t)
    rice.draw(img, t)
    shot = shot_at(t)
    band.draw(img, t, shot_id=shot.id if shot else None,
              shot_t0=shot.t0 if shot else 0.0)
    # prev=None whenever the frame carries Chinese that must stay crisp: the trail
    # is a "lighter" blend, i.e. the previous frame double-exposes onto this one.
    return kit.post(img, prev, TRAIL, BLOOM)


# ---------------------------------------------------------------- the frame loop
def _chunk(job):
    i0, i1, outdir = job
    outdir = Path(outdir)
    prev = None
    for i in range(i0, i1):
        img = render_frame(i / FPS, prev)
        img.save(outdir / f"f_{i:06d}.png")
        prev = img
    return i1 - i0


def render(t0: float, t1: float, outdir: Path, workers: int) -> None:
    n0, n1 = int(math.floor(t0 * FPS)), int(math.ceil(t1 * FPS))
    outdir.mkdir(parents=True, exist_ok=True)
    total = n1 - n0
    if workers <= 1 or total < 4 * FPS:
        _chunk((n0, n1, str(outdir)))
        print(f"rendered {total} frames -> {outdir}")
        return
    per = max(FPS, total // workers)
    jobs = [(i, min(i + per, n1), str(outdir)) for i in range(n0, n1, per)]
    print(f"{total} frames in {len(jobs)} chunks across {workers} threads", flush=True)
    # Threads, not processes: on Windows multiprocessing builds its own named pipes
    # for the executor, and a sandboxed host may deny opening them (WinError 5).
    # PIL releases the GIL inside its C calls, so threads still run in parallel.
    with ThreadPoolExecutor(max_workers=workers) as ex:
        done = 0
        for k in ex.map(_chunk, jobs):
            done += k
            print(f"  {done}/{total}", flush=True)
    print(f"rendered {total} frames -> {outdir}")


def sheet(frames: Path, out: Path, cols: int = 6, max_tiles: int = 60) -> None:
    """Tile a strip of frames for review.

    A long strip cannot be tiled whole -- 1000 frames at a readable thumb size is
    a 46 000 px column. So the strip is sampled down to at most `max_tiles`, which
    keeps the sheet readable whatever the strip length.
    """
    files = sorted(frames.glob("f_*.png"))
    if not files:
        sys.exit(f"no frames in {frames}")
    step = max(1, len(files) // max_tiles)
    picked = files[::step][:max_tiles]
    tw = max(160, 1280 // cols)
    th = tw * 9 // 16
    thumbs = [Image.open(f).resize((tw, th), Image.LANCZOS) for f in picked]
    rows = (len(thumbs) + cols - 1) // cols
    canvas = Image.new("RGB", (tw * cols, th * rows), (0, 0, 0))
    d = ImageDraw.Draw(canvas)
    for i, im in enumerate(thumbs):
        x, y = (i % cols) * tw, (i // cols) * th
        canvas.paste(im, (x, y))
        d.rectangle([x, y, x + tw - 1, y + th - 1], outline=(40, 44, 58))
        d.text((x + 3, y + 2), picked[i].stem.split("_")[1], fill=(255, 210, 120))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"{len(picked)} of {len(files)} frames -> {out} ({canvas.width}x{canvas.height})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["all", "strip", "range", "sheet"])
    ap.add_argument("a", nargs="?", type=float)
    ap.add_argument("b", nargs="?", type=float)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--out", default="")
    ap.add_argument("--sheet", default="",
                    help="contact sheet path; keep it per-run so parallel runs"
                         " do not overwrite each other")
    a = ap.parse_args()
    sheet_path = Path(a.sheet) if a.sheet else config.OUT / "sheet.png"

    if a.step == "strip":
        t0, t1 = (a.a or 0.0), (a.b or (a.a or 0.0) + 3.0)
        out = Path(a.out) if a.out else config.OUT / "review"
        if out.exists():
            shutil.rmtree(out)
        render(t0, t1, out, 1)
        sheet(out, sheet_path)
    elif a.step == "sheet":
        sheet(Path(a.out) if a.out else config.OUT / "review", sheet_path)
    elif a.step == "range":
        # re-render part of an existing frame set in place (frames keep their
        # global numbering, so the sequence stays contiguous for the encoder)
        if a.a is None or a.b is None:
            ap.error("range needs a start and an end time")
        render(a.a, a.b, Path(a.out) if a.out else config.OUT / "frames", a.workers)
    else:
        render(0.0, _timeline()["duration"],
               Path(a.out) if a.out else config.OUT / "frames", a.workers)


if __name__ == "__main__":
    main()
