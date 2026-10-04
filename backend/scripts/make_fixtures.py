"""Regenerate the reference skin and golden nets. Owner-only: goldens are a contract.

Usage: uv run python scripts/make_fixtures.py
"""

import colorsys
from pathlib import Path

import numpy as np

from real2block.domain.papercraft.net import render_debug_png
from real2block.domain.skin.geometry import FACE_IDS, PART_IDS, face_rect
from real2block.domain.skin.skin import Skin

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
MARKER_FIRST = (255, 255, 255, 255)
MARKER_SECOND = (0, 0, 0, 255)
# Spreads consecutive faces far apart on the hue wheel so neighbours differ.
GOLDEN_RATIO = 0.618033988749895


def reference_pixels() -> np.ndarray:
    """Unique opaque color per base face; white top-left and black top-right markers."""
    out = np.zeros((64, 64, 4), dtype=np.uint8)
    for index, (part, face) in enumerate((p, f) for p in PART_IDS for f in FACE_IDS):
        r, g, b = colorsys.hsv_to_rgb((index * GOLDEN_RATIO) % 1.0, 0.65, 0.85)
        rect = face_rect(part, face)
        region = out[rect.y : rect.y + rect.h, rect.x : rect.x + rect.w]
        region[...] = (round(r * 255), round(g * 255), round(b * 255), 255)
        region[0, 0] = MARKER_FIRST
        region[0, -1] = MARKER_SECOND
    return out


def main() -> None:
    """Write reference_skin.png and reference_net_<part>.png."""
    FIXTURES.mkdir(parents=True, exist_ok=True)
    skin = Skin(reference_pixels())
    (FIXTURES / "reference_skin.png").write_bytes(skin.to_png())
    for part in PART_IDS:
        (FIXTURES / f"reference_net_{part}.png").write_bytes(
            render_debug_png(skin, part, "classic")
        )


if __name__ == "__main__":
    main()
