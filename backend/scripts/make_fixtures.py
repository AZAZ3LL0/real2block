"""Regenerate the reference skin, golden nets and stylizer goldens. Owner-only: a contract.

Usage: uv run python scripts/make_fixtures.py
"""

import colorsys
from pathlib import Path
from typing import get_args

import numpy as np

from real2block.api.schemas import SkinSpec
from real2block.domain.papercraft.net import render_debug_png
from real2block.domain.skin.geometry import FACE_IDS, PART_IDS, Model, face_rect
from real2block.domain.skin.skin import Skin
from real2block.domain.stylize.base import HAIR_STYLES
from real2block.domain.stylize.grids import TEMPLATES_DIR, load_template_dir
from real2block.domain.stylize.template import TemplateStylizer

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


def write_stylizer_goldens() -> None:
    """Render stylize_spec.json with every hair style and model to stylize_<style>_<model>.png."""
    stylizer = TemplateStylizer.from_templates(load_template_dir(TEMPLATES_DIR))
    spec = SkinSpec.model_validate_json((FIXTURES / "stylize_spec.json").read_text())
    for style in HAIR_STYLES:
        for model in get_args(Model):
            variant = spec.model_copy(update={"hair_style": style, "model": model})
            skin = stylizer.render(variant.to_domain())
            (FIXTURES / f"stylize_{style}_{model}.png").write_bytes(skin.to_png())


def main() -> None:
    """Write reference_skin.png, reference_net_<part>.png and the stylizer goldens."""
    FIXTURES.mkdir(parents=True, exist_ok=True)
    skin = Skin(reference_pixels())
    (FIXTURES / "reference_skin.png").write_bytes(skin.to_png())
    for part in PART_IDS:
        (FIXTURES / f"reference_net_{part}.png").write_bytes(
            render_debug_png(skin, part, "classic")
        )
    write_stylizer_goldens()


if __name__ == "__main__":
    main()
