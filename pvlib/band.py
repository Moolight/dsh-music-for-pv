"""The lyric band: the current line, lighting up character by character.

Engine, not content. The band is told which lines are whole-sentence decodes and
which shots are deliberately wordless; it does not know this film's numbers.

    band = LyricBand(timeline["lines"], decode_lines={63, 64},
                     no_lyric={"S10"}, no_lyric_head={"S55": 2.0})
    band.draw(img, t, shot_id="S10")
"""
from __future__ import annotations

import random

from PIL import Image, ImageDraw, ImageFont

from pvlib import kit

# 24 px is the comfortable body size on a 1280x720 canvas; 18 px is the floor and
# 14 px is annotations only (measured -- see docs/cjk-notes.md). The band sits
# over the bottom of the frame, which the default vignette used to crush; kit
# turns LYRIC_LIFT on at import.
BAND_Y0, BAND_Y1 = 626, 700
LINE_PX = 24
F_CJK = ImageFont.truetype(kit.F_CJK, LINE_PX)
F_CJK_S = ImageFont.truetype(kit.F_CJK, 16)
HOLD, FADE = 0.35, 0.45          # hold a finished line, then fade it out


def char_times(text: str, words: list) -> list[tuple[str, float | None]]:
    """Every character of the line -- spaces included -- with the time it is sung.

    Spaces must stay in the list: dropping them collapses "Let me go" to
    "Letmego" and loses the word gaps. They carry no time and are not drawn.

    The word list cannot be matched character by character: a Chinese ASR
    returns traditional forms (別飛魚) against a simplified sheet (别飞鱼), and it
    also drops or merges words. So the word characters are flattened and spread
    positionally across the line instead -- exact when the counts line up,
    proportional when they do not. That also makes this work unchanged for Latin
    lyrics.
    """
    plain = [c for c in text if c.strip()]
    if not plain:
        return []
    flat = [(c, float(w.get("t", 0.0)))
            for w in words for c in str(w.get("w", "")) if c.strip()]
    if not flat:
        return [(c, None) for c in text]

    times: dict[int, float] = {}
    if len(flat) == len(plain):
        times = {i: t for i, (_c, t) in enumerate(flat)}
    else:
        n, m = len(plain), len(flat)
        for i in range(n):
            j = int(round(i * (m - 1) / (n - 1))) if n > 1 else 0
            times[i] = flat[j][1]

    out, k = [], 0
    for c in text:
        if c.strip():
            out.append((c, times.get(k)))
            k += 1
        else:
            out.append((c, None))
    return out


class LyricBand:
    def __init__(self, lines: list, decode_lines=frozenset(), no_lyric=frozenset(),
                 no_lyric_head: dict | None = None, debug: bool = False):
        self.lines = lines
        self.decode = set(decode_lines)
        self.no_lyric = set(no_lyric)
        self.no_lyric_head = dict(no_lyric_head or {})
        self.debug = debug

    def line_at(self, t: float):
        """-> (line dict, 0-based index) or (None, -1)."""
        lines = self.lines
        lo, hi, best = 0, len(lines) - 1, -1
        while lo <= hi:
            m = (lo + hi) // 2
            if lines[m]["t"] <= t:
                best, lo = m, m + 1
            else:
                hi = m - 1
        return (None, -1) if best < 0 else (lines[best], best)

    def draw(self, img: Image.Image, t: float, shot_id: str | None = None,
             shot_t0: float = 0.0) -> None:
        W, H = kit.W, kit.H
        d = ImageDraw.Draw(img)
        line, idx = self.line_at(t)

        # deliberately wordless shots
        if shot_id is not None:
            if shot_id in self.no_lyric:
                return
            head = self.no_lyric_head.get(shot_id)
            if head is not None and (t - shot_t0) < head:
                return

        # SHOTS.md 4.2: once the line is sung it holds, then fades out. Without
        # this the final line, which ends 11 s before the song does, sits there
        # through the ending. Computed before drawing so the strip and its rule
        # fade with the words. It only applies inside a gap: as soon as the next
        # line starts, line_at has already moved on.
        fade = 1.0
        if line is not None:
            ends = [float(w.get("end", line["t"])) for w in (line.get("words") or [])]
            tail = max(ends) if ends else float(line["t"])
            if t > tail + HOLD:
                fade = max(0.0, 1.0 - (t - tail - HOLD) / FADE)
                if fade <= 0.02:
                    return

        d.rectangle([16, BAND_Y0 - 6, W - 16, BAND_Y1 + 4], fill=(2, 4, 9))
        d.line([24, BAND_Y0 - 8, W - 24, BAND_Y0 - 8], fill=kit.amb(0.25 * fade))
        if line is None:
            return

        if idx + 1 in self.decode:
            # whole-sentence decode: the line resolves out of glyph noise, no
            # per-character highlight (rate 14 suits Chinese; 45 is far too fast)
            age = t - float(line["t"])
            shown = kit.decode(line["text"], age, random.Random(idx), rate=14.0, settle=0.35)
            x = 28
            for ch in shown:
                d.text((x, BAND_Y0 + 4), ch, font=F_CJK,
                       fill=kit.blue(0.98 * fade) if age > 0.5
                       else kit.mix(kit.UI, 0.45 * fade))
                x += F_CJK.getlength(ch)
        else:
            x = 28
            for ch, wt in char_times(line["text"], line.get("words") or []):
                if not ch.strip():          # spaces carry no ink but still advance
                    x += F_CJK.getlength(ch)
                    continue
                on = wt is not None and t >= wt
                d.text((x, BAND_Y0 + 4), ch, font=F_CJK,
                       fill=kit.blue(0.98 * fade) if on else kit.amb(0.32 * fade))
                x += F_CJK.getlength(ch)
                if x > W - 36:
                    break

        if self.debug:
            d.text((28, BAND_Y1 - 14), str(line.get("block", "")),
                   font=F_CJK_S, fill=kit.amb(0.30))
            d.text((W - 150, BAND_Y1 - 14), f"{t:6.2f}s",
                   font=kit.font(kit.F_MONO, 14), fill=kit.amb(0.30))
