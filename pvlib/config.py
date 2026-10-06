"""Where the things this repository does not own live.

Nothing third-party is redistributed here: the song, the character art, the
sticker pack and the TUI engine all belong to someone else or to the operator.
Every one of them can be pointed at with an environment variable, and each has a
default that works when the layout matches the original machine.

    PV_TUI          the tuikit engine -- upstream world-execute-me-dsh-pv,
                    `film/tui_pv_world_execute_20260926/` (MIT, MisakaZentai)
    PV_MEME_PACKS   DSH meme packs; default ~/.dsh/meme-packs
    PV_SONG         the audio to mux into the film
    PV_WHISPER      whisper word-timestamp JSON, used to build the timeline
    PV_LYRICS       the lyric sheet (one line per sung line, with [Section] tags)
    PV_LRC          the line-level LRC
    PV_COMFY_ART    a folder of chibi art; only chibi.py reads it, and the
                    released film does not use chibi.py at all
    PV_STICKER_PACK which pack in PV_MEME_PACKS to use

`input/` is where your own copies go; it is gitignored and empty in the repo.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent     # the checkout root
ROOT = PROJECT
INPUT = PROJECT / "input"
OUT = PROJECT / "out"


def _p(env: str, default: Path | str | None = None, must_exist: bool = False) -> Path | None:
    v = os.environ.get(env)
    p = Path(v).expanduser() if v else (Path(default).expanduser() if default else None)
    if p is not None and must_exist and not p.exists():
        return None
    return p


# --- the TUI engine -------------------------------------------------------
# The toolkit is vendored, so this project runs on its own. PV_TUI is only for
# working against a clone of the upstream repository instead of the vendored copy.
TUI = _p("PV_TUI")
VENDOR_TUI = PROJECT / "pvlib" / "vendor"

# assets shipped with the project: the toolkit's fonts (SIL OFL) and the
# character sprites (CC BY-NC-SA 4.0). See assets/README.md.
ASSETS = _p("PV_ASSETS", PROJECT / "assets")
SPRITES = _p("PV_SPRITES", PROJECT / "assets" / "sprites")

MEME_PACKS = _p("PV_MEME_PACKS", Path.home() / ".dsh" / "meme-packs")
STICKER_PACK = os.environ.get("PV_STICKER_PACK", "whale-girl-emoji")

# --- the film's own inputs (your copies live in input/) -------------------
SONG = _p("PV_SONG", INPUT / "song.flac")
LYRICS = _p("PV_LYRICS", INPUT / "lyrics.txt")
LRC = _p("PV_LRC", INPUT / "lyrics.lrc")
WHISPER = _p("PV_WHISPER", INPUT / "whisper_words.json")


def check() -> list[str]:
    """Human-readable list of what is missing, for the CLI to print."""
    problems = []
    for label, p in (("vendored tuikit", VENDOR_TUI / "tuikit.py"),
                     ("assets", ASSETS),
                     ("sprites", SPRITES)):
        if not Path(p).exists():
            problems.append(f"{label} not found at {p}")
    if not Path(MEME_PACKS).exists():
        problems.append(f"meme packs not found at {MEME_PACKS} (set PV_MEME_PACKS)")
    elif not (Path(MEME_PACKS) / STICKER_PACK).exists():
        problems.append(
            f"sticker pack '{STICKER_PACK}' not in {MEME_PACKS}"
            f" (set PV_STICKER_PACK; installed: "
            f"{', '.join(sorted(p.name for p in Path(MEME_PACKS).iterdir() if p.is_dir()))})")
    for label, p in (("song", SONG), ("lyrics", LYRICS), ("lrc", LRC)):
        if p and not Path(p).exists():
            problems.append(f"{label} not found at {p} (see input/README.md)")
    return problems


if __name__ == "__main__":
    print(f"root          {PROJECT}")
    for name in ("VENDOR_TUI", "ASSETS", "SPRITES", "MEME_PACKS",
                 "SONG", "LYRICS", "LRC", "WHISPER"):
        v = globals()[name]
        mark = "(unset)" if v is None else ("ok" if Path(v).exists() else "MISSING")
        print(f"{name:<13} {v}   {mark}")
    pack_dir = Path(MEME_PACKS) / STICKER_PACK
    print(f"{'STICKER_PACK':<13} {STICKER_PACK}   "
          f"{'ok' if pack_dir.exists() else 'MISSING'}")
    print(f"{'TUI':<13} {TUI or '(vendored under pvlib/vendor)'}")
    problems = check()
    print()
    for p in problems:
        print("! " + p)
    if not problems:
        print("all inputs present")
