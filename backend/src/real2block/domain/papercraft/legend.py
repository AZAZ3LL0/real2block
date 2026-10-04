"""Color legend, numbering and palette reduction for printing (tech.md §4.5)."""

from collections import Counter
from dataclasses import dataclass
from typing import Literal

import numpy as np

from real2block.domain.color import Rgb, quantize
from real2block.domain.skin.geometry import FACE_IDS, PART_IDS, Model, Rect, face_rect
from real2block.domain.skin.skin import Skin

PrintMode = Literal["color", "numbered"]

NUMBERED_MAX_COLORS = 16
COLOR_LEGEND_MAX = 32


@dataclass(frozen=True, slots=True)
class LegendEntry:
    """One palette color with its number and how many cells it covers."""

    number: int
    color: Rgb
    cells: int


@dataclass(frozen=True, slots=True)
class Legend:
    """Numbered colors by decreasing cell count; the tail beyond the limit is summed up."""

    mode: PrintMode
    entries: tuple[LegendEntry, ...]
    other_cells: int

    def number_of(self, color: Rgb) -> int | None:
        """Number printed for a color, if it made it into the table."""
        return next((e.number for e in self.entries if e.color == color), None)


@dataclass(frozen=True, slots=True)
class PreparedSkin:
    """Skin ready for printing, with its legend and whether colors were merged."""

    skin: Skin
    legend: Legend
    reduced: bool


def _base_rects(model: Model) -> list[Rect]:
    return [face_rect(part, face, model=model) for part in PART_IDS for face in FACE_IDS]


def cell_colors(skin: Skin, model: Model) -> list[Rgb]:
    """Color of every printed cell: all base-layer face pixels."""
    return [skin.rgb_at(x, y) for rect in _base_rects(model) for x, y in rect.cells()]


def build_legend(colors: list[Rgb], mode: PrintMode) -> Legend:
    """Number colors 1..N by decreasing count; ties are broken by RGB for stable output."""
    limit = NUMBERED_MAX_COLORS if mode == "numbered" else COLOR_LEGEND_MAX
    counts = Counter(colors)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0].r, item[0].g, item[0].b))
    entries = tuple(
        LegendEntry(i, color, n) for i, (color, n) in enumerate(ranked[:limit], start=1)
    )
    return Legend(mode, entries, sum(n for _, n in ranked[limit:]))


def _recolor(skin: Skin, model: Model, mapping: dict[Rgb, Rgb]) -> Skin:
    pixels = skin.pixels.copy()
    for rect in _base_rects(model):
        for x, y in rect.cells():
            new = mapping[skin.rgb_at(x, y)]
            pixels[y, x, :3] = np.array([new.r, new.g, new.b], dtype=np.uint8)
    return Skin(pixels)


def prepare_skin(skin: Skin, model: Model, mode: PrintMode) -> PreparedSkin:
    """Reduce to 16 colors in numbered mode, then count and number the cells."""
    colors = cell_colors(skin, model)
    reduced = False
    if mode == "numbered":
        mapping = quantize(colors, NUMBERED_MAX_COLORS)
        reduced = len(set(mapping.values())) < len(mapping)
        skin = _recolor(skin, model, mapping)
        colors = [mapping[c] for c in colors]
    return PreparedSkin(skin, build_legend(colors, mode), reduced)
