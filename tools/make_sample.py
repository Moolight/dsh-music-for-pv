"""Render a short window of the film and encode it with the matching audio.

This is the review loop: pick a window, get a small mp4 that plays with the song,
so the visuals can be judged against what is being sung rather than as stills.

    python make_sample.py --at 43.76 --dur 10          the first chorus
    python make_sample.py --at 145.58 --dur 10 --name key
    python make_sample.py --shots S32 S33 S34          one window per named shot

Without --shots it renders one window starting at --at.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from pvlib import config as _cfg  # noqa: E402

SONG = Path(_cfg.SONG)
PY = sys.executable


def run(cmd):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, cwd=PROJECT)


def window(t0: float, dur: float, name: str) -> Path:
    frames = PROJECT / "out" / f"_review_{name}"
    if frames.exists():
        shutil.rmtree(frames)
    run([PY, "render.py", "strip", f"{t0:.3f}", f"{t0 + dur:.3f}",
         "--out", str(frames), "--sheet", str(PROJECT / "out" / f"sheet_{name}.png")])
    out = PROJECT / "out" / f"sample_{name}.mp4"
    run([PY, "encode.py", str(frames), "--song", str(SONG), "--out", str(out),
         "--duration", f"{dur:.3f}", "--audio-ss", f"{t0:.3f}"])
    print(f"-> {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", type=float, default=0.0, help="start time in the song")
    ap.add_argument("--dur", type=float, default=10.0)
    ap.add_argument("--name", default="win")
    ap.add_argument("--shots", nargs="*", default=None,
                    help="render one window per named shot (S01 ...) instead")
    a = ap.parse_args()

    if a.shots:
        import json
        rows = {r["id"]: r for r in json.loads(
            (PROJECT / "out" / "shots.json").read_text(encoding="utf8"))}
        for sid in a.shots:
            r = rows.get(sid)
            if r is None:
                print("no such shot:", sid)
                continue
            window(r["t0"], min(a.dur, r["t1"] - r["t0"]), sid)
    else:
        window(a.at, a.dur, a.name)


if __name__ == "__main__":
    main()
