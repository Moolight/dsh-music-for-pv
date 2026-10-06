"""Compose the cover still.

Not a frame grab: a purpose-made 16:9 poster in the film's own visual language
(deep-sea palette, the dot field, her as a halftone sprite, the TUI panel frame),
plus the parts a cover needs that a shot never shows -- the title at a readable
size, and the credit line.

Everything is laid out in units of the 1280x720 design grid and multiplied by
`scale`, so `--scale 3` produces a 3840x2160 poster with the sprite re-rendered at
that resolution rather than upscaled.

    python cover.py out/cover.png
    python cover.py out/cover_4k.png --scale 3
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))

from pvlib import kit  # noqa: E402
from pvlib.assets import logo as whale_mark  # noqa: E402

W, H = kit.W, kit.H
F_CJK = "C:/Windows/Fonts/msyh.ttc"
F_CJK_B = "C:/Windows/Fonts/msyhbd.ttc"

TITLE_CN = "请叫我"
TITLE_EN = "DEEPSEEK"
LYRIC = "白饭是我的燃料"
FOOT = "音乐 YuE2 3B　·　PV dsh 鲸鱼娘　·　视觉语言 MisakaZentai"
BYLINE = "非官方同人作品 · 全片由 AI 生成"

PANEL = (28, 28, W - 28, H - 28)
# `full` crops to the alpha bounding box, so her silhouette has no straight cut
# edges showing; the fixed-fraction crops (bust, upper) end mid-body and leave a
# hard line. Her feet sit on the panel's bottom edge.
HER_CROP, HER_X, HER_W, HER_MAXH = "full", 95, 340, 580
HER_BOTTOM = PANEL[3]
TX = 604                                     # left edge of the title column


def compose(scale: int = 1) -> Image.Image:
    s = scale
    w, h = W * s, H * s
    img = Image.new("RGB", (w, h), kit.BG)
    # kept so the panel label can restore the field under itself later
    field = kit.dot_field(W, H - 16).resize((W * s, (H - 16) * s), Image.NEAREST)
    img.paste(field, (0, 0))
    d = ImageDraw.Draw(img)

    def px(*v):
        return tuple(int(x * s) for x in v)

    # --- her, halftone dots in the brand blue, rendered at output resolution --
    her = kit.halfblock(HER_CROP and "starry", HER_CROP, HER_W * s, HER_MAXH * s,
                        px=4 * s, tint="blue")
    img.paste(her, px(HER_X, HER_BOTTOM - her.height // s), her)

    # --- the blocky Latin wordmark. Anton has no hanzi, so the Chinese title
    #     goes through a CJK face and the Latin through banner_block, as in the
    #     film's own banners. -------------------------------------------------
    mark = kit.banner_block(TITLE_EN, 15, 7 * s, kit.BLUE_HI, kit.BG, max_w=580 * s)
    d.text(px(TX, 150), TITLE_CN, font=ImageFont.truetype(F_CJK_B, 40 * s), fill=kit.UI)
    img.paste(mark, px(TX, 214), mark)

    rule_y = 214 + mark.height // s + 22
    d.line([*px(TX, rule_y), *px(TX + 580, rule_y)], fill=kit.amb(0.34))

    d.text(px(TX, rule_y + 18), "PV", font=ImageFont.truetype(F_CJK_B, 26 * s),
           fill=kit.BLUE_TEXT)
    d.text(px(TX + 70, rule_y + 22), "4:28",
           font=ImageFont.truetype(F_CJK, 19 * s), fill=kit.mix(kit.UI, 0.70))

    # --- the song's motif: a dotted bowl, and the line it comes from ----------
    by = rule_y + 96
    cx = TX + 44
    for i, r in enumerate((3, 5, 6, 6, 5, 3)):          # rice mound
        d.ellipse([*px(cx - 34 + i * 12 - r, by - r), *px(cx - 34 + i * 12 + r, by + r)],
                  fill=kit.blue(0.78))
    d.arc([*px(cx - 44, by - 4), *px(cx + 44, by + 46)], 0, 180, fill=kit.amb(0.72),
          width=max(1, 2 * s))
    for i, ch in enumerate(LYRIC):
        d.text(px(cx + 66 + i * 21, by + 2), ch,
               font=ImageFont.truetype(F_CJK, 19 * s), fill=kit.mix(kit.UI, 0.84))

    # --- the whale mark: small, and clear of every text line -----------------
    wm = whale_mark.whale(132 * s, 99 * s, tint=kit.BLUE_MID, kind="solid")
    img.paste(wm, px(TX, rule_y + 172), wm)

    # --- type at the foot of the panel. Both lines live in the right column:
    #     the left one is her, and text over the halftone is unreadable. --------
    f_foot = ImageFont.truetype(F_CJK, 16 * s)
    d.text(px(TX, H - 96), BYLINE, font=f_foot, fill=kit.amb(0.5))
    d.text(px(TX, H - 70), FOOT, font=f_foot, fill=kit.amb(0.44))

    # --- the panel frame, and its label --------------------------------------
    # kit.box() writes its title on a flat BG rectangle to knock the border out
    # from behind it. That is fine over a solid background, but this cover's
    # background is the dot field, so the flat patch reads as an inexplicable
    # darker notch. Draw the frame with no title, put the FIELD back under the
    # label, then draw the text -- the border ends up with a clean gap in it.
    kit.box(d, *px(*PANEL), level=0.4)

    label = "call me deepseek"
    f_lab = kit.font(kit.F_HEAD, 13 * s)     # box() would not have scaled this
    lx, ly = PANEL[0] + 12, PANEL[1] - 10
    lw, lh = int(d.textlength(" " + label + " ", font=f_lab)), 20 * s
    img.paste(field.crop((lx * s, ly * s, lx * s + lw, ly * s + lh)), (lx * s, ly * s))
    d.text(px(lx, ly + 1), " " + label + " ", font=f_lab, fill=kit.amb(0.66))

    # kit.vignette() and kit.scanlines() are built at the film's 1280x720 and are
    # cached that way. alpha_composite does NOT resize: given a bigger canvas it
    # silently composites only the overlapping top-left corner, which leaves the
    # vignette and scanlines covering one quadrant and shows up as a hard-edged
    # dark rectangle in the upper left. Scale them to the canvas first.
    img = img.convert("RGBA")
    img.alpha_composite(kit.scanlines().resize((w, h), Image.NEAREST))
    img.alpha_composite(kit.vignette(False).resize((w, h), Image.BILINEAR))
    return img.convert("RGB")


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "out" / "cover.png"
    scale = int(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 1
    out.parent.mkdir(parents=True, exist_ok=True)
    compose(scale).save(out)
    print(f"-> {out}  ({W * scale}x{H * scale})")


if __name__ == "__main__":
    main()
