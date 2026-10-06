"""Scene dispatcher: routes song time to whichever shot module owns it.

The shots live in `content/acts/`, five modules, one per act group, so they can
be written in parallel. The list is passed in rather than hardcoded, so the
engine does not know anything about this particular film -- a different film
supplies its own act list.

Each module exposes:

    SHOTS = {"S01": draw_s01, "S02": draw_s02, ...}

A module that is missing, or that fails to import, is reported by `missing()`
and simply skipped: the rest of the film stays renderable.
"""
from __future__ import annotations

import importlib

from PIL import ImageDraw

from pvlib.kit import shot_at

# where this film's shots come from; override to reuse the engine elsewhere
MODULES = [f"content.acts.act{i}" for i in range(1, 6)]

_REG: dict | None = None
_MISSING: list[str] = []


def registry() -> dict:
    global _REG
    if _REG is None:
        _REG = {}
        for name in MODULES:
            try:
                mod = importlib.import_module(name)
            except ImportError as e:
                _MISSING.append(f"{name}: {e}")
                continue
            except Exception as e:
                # A module that exists but fails to import (NameError, syntax slip)
                # must not take the whole film down -- report it and keep going.
                _MISSING.append(f"{name}: {type(e).__name__}: {e}")
                continue
            _REG.update(getattr(mod, "SHOTS", {}))
    return _REG


def missing() -> list[str]:
    registry()
    return list(_MISSING)


def draw(img, t: float) -> None:
    s = shot_at(t)
    if s is None:
        return
    fn = registry().get(s.id)
    if fn is None:
        return
    fn(img, ImageDraw.Draw(img), t, s)
