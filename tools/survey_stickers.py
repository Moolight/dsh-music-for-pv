"""Build captioned contact sheets for a DSH meme pack.

Packs live under ~/.dsh/meme-packs/<id>/ with memes/<tag>/<file> and an index.db
holding a caption per sticker. Picking one per lyric line means seeing the
picture and its line together, so this renders one sheet per emotion with the
caption underneath.

    python survey_stickers.py                          the default pack
    python survey_stickers.py --pack whale-girl-emoji
    python survey_stickers.py --list                   what is installed
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pvlib import config as _cfg  # noqa: E402

PACKS = Path(_cfg.MEME_PACKS)
F_CJK = "C:/Windows/Fonts/msyh.ttc"
F_MONO = "C:/Windows/Fonts/consola.ttf"

CW, CH = 190, 232          # cell
IMG = 166                  # sticker box
COLS = 6


def list_packs() -> None:
    for p in sorted(PACKS.iterdir()):
        mf = p / "manifest.json"
        if not (p.is_dir() and mf.exists()):
            continue
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            m = {}
        n = len(list((p / "memes").rglob("*.*"))) if (p / "memes").exists() else 0
        print(f"  {p.name:<22} {n:>4} 张   license={m.get('license', '(未声明)'):<18} "
              f"维护者={m.get('maintainer', '-')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default="deepseek-chan")
    ap.add_argument("--out", default="")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list:
        list_packs()
        return

    pack = PACKS / a.pack
    OUT = Path(a.out) if a.out else Path(__file__).resolve().parent / "out"
    db = sqlite3.connect(pack / "index.db")
    rows = db.execute("SELECT path, tag, caption FROM memes ORDER BY tag, file_name").fetchall()
    mf = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    print(f"{len(rows)} stickers  pack={a.pack}  license={mf.get('license', '(none)')}")
    tag_font = ImageFont.truetype(F_CJK, 15)
    cap_font = ImageFont.truetype(F_CJK, 12)
    id_font = ImageFont.truetype(F_MONO, 11)

    by_tag: dict[str, list] = {}
    for path, tag, caption in rows:
        by_tag.setdefault(tag, []).append((path, caption))

    index = []
    for tag, items in sorted(by_tag.items()):
        rowsn = (len(items) + COLS - 1) // COLS
        canvas = Image.new("RGB", (CW * COLS, CH * rowsn + 26), (10, 12, 18))
        d = ImageDraw.Draw(canvas)
        d.text((6, 6), f"{tag}  ({len(items)})", font=tag_font, fill=(255, 210, 120))
        for i, (path, caption) in enumerate(items):
            x, y = (i % COLS) * CW, 26 + (i // COLS) * CH
            f = pack / path
            try:
                im = Image.open(f).convert("RGB")
                im.thumbnail((IMG, IMG), Image.LANCZOS)
                canvas.paste(im, (x + (CW - im.width) // 2, y + 4))
            except Exception as e:
                d.text((x + 6, y + 20), f"ERR {e}"[:24], font=cap_font, fill=(255, 90, 90))
            name = f"{tag}/{f.stem}"
            d.text((x + 5, y + IMG + 6), name, font=id_font, fill=(150, 200, 255))
            for k, chunk in enumerate(textwrap.wrap(str(caption or ""), 13)[:3]):
                d.text((x + 5, y + IMG + 20 + k * 13), chunk, font=cap_font, fill=(210, 210, 215))
            d.rectangle([x, y, x + CW - 1, y + CH - 1], outline=(38, 42, 56))
            index.append((name, caption))
        out = OUT / f"stickers_{a.pack}_{tag}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out)
        print("->", out, canvas.size)

    with (OUT / f"stickers_{a.pack}_index.txt").open("w", encoding="utf-8") as fh:
        for name, cap in index:
            fh.write(f"{name}\t{cap}\n")
    print("->", OUT / "stickers_index.txt")


if __name__ == "__main__":
    main()
