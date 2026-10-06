"""Overlay tracks: things laid over the scene on their own timecode.

Engine, not content. Each track is handed its cues (or its meter) from the
content layer, so the same classes drive a different film by passing different
tables.

    track = StickerTrack(cues.STICKERS, place=json.loads(...), alpha=cues.STICKER_ALPHA)
    track.draw(img, t)

    meter = RiceMeter(content.rice)
    meter.draw(img, t)
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from pvlib import kit
from pvlib.kit import ease


class StickerTrack:
    """Stickers laid over the scene, faded and slid in as each cue arrives.

    Cues are `(t_in, t_out, tag, name, x, y, width)`. `place` optionally overrides
    the position and size per cue -- see `tools/place_stickers.py`, which measures
    the spot that hides the least of the scene.
    """

    def __init__(self, cues, place: dict | None = None, alpha: float = 0.92,
                 pack: str | None = None):
        self.cues = list(cues)
        self.place = dict(place or {})
        self.alpha = alpha
        self.pack = pack
        self._cache: dict = {}

    def _figure(self, tag: str, name: str, w: int):
        from pvlib.assets import stickers as stk

        key = (tag, name, w)
        if key not in self._cache:
            try:
                # background knocked out, so the sticker reads as the character
                # standing in the scene rather than an opaque card pasted on top
                self._cache[key] = stk.figure(tag, name, w, int(w * 1.35),
                                              pack_id=self.pack)
            except Exception:
                self._cache[key] = None
        return self._cache[key]

    def draw(self, img: Image.Image, t: float) -> None:
        for t0, t1, tag, name, x, y, w in self.cues:
            if not (t0 <= t < t1):
                continue
            pos = self.place.get(f"{tag}/{name}")
            if pos:
                x, y, w = int(pos[0]), int(pos[1]), int(pos[2])
            fig = self._figure(tag, name, w)
            if fig is None:
                continue
            rise = 26 * (1.0 - ease(min(1.0, (t - t0) / 0.42)))
            fade = min(1.0, (t - t0) / 0.28) * min(1.0, (t1 - t) / 0.34)
            if fade <= 0.01:
                continue
            ghost = fig.copy()
            ghost.putalpha(ghost.getchannel("A").point(
                lambda v: int(v * fade * self.alpha)))
            img.paste(ghost, (x, int(y + rise)), ghost)


class RiceMeter:
    """A small readout of a running total, shown only while it is advancing.

    `meter` is anything with `rate(t)`, `total(t)` and `active(t)` -- the film
    passes its own `content.rice`. Drawing the running figure on screen is what
    makes the number on the end card one the film actually showed.
    """

    def __init__(self, meter, at: tuple[int, int] = (28, 96), size: int = 15,
                 label: str = "rice", unit: str = "g"):
        self.meter = meter
        self.at = at
        self.size = size
        self.label = label
        self.unit = unit

    def draw(self, img: Image.Image, t: float) -> None:
        if not self.meter.active(t):
            return
        d = ImageDraw.Draw(img)
        x, y = self.at
        lv = 0.92 if self.meter.rate(t) >= 3.0 else 0.7
        d.rectangle([x - 4, y + 4, x - 2, y + 12], fill=kit.blue(min(1.0, lv + 0.06)))
        d.text((x, y), f"{self.label} {self.meter.total(t):05.0f} {self.unit}",
               font=kit.font(kit.F_MONO, self.size), fill=kit.blue(lv))


def load_placement(path: Path) -> dict:
    """Read a placement table; a missing table just means "use the cue's x/y"."""
    import json

    try:
        return json.loads(Path(path).read_text(encoding="utf8"))
    except Exception:
        return {}
