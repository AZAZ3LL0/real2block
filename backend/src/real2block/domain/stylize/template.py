"""Template stylizer: hair and outfit `.grid` files painted with the palette (tech.md §5.3)."""

from collections.abc import Mapping
from types import MappingProxyType

import numpy as np

from real2block.domain.color import darken
from real2block.domain.skin.geometry import FACE_IDS, PART_IDS, SKIN_SIZE, PartId
from real2block.domain.skin.skin import Pixels, Skin
from real2block.domain.stylize.base import HAIR_STYLES, HairStyle, Palette, SkinSpec
from real2block.domain.stylize.grids import GridTemplate, TemplateError
from real2block.domain.stylize.roles import SYMBOLS

OUTFIT_TEMPLATE = "outfit_tshirt"
HAIR_PARTS: frozenset[PartId] = frozenset({"head"})
OUTFIT_PARTS: frozenset[PartId] = frozenset(PART_IDS) - HAIR_PARTS
OPAQUE = 255


def hair_template_name(style: HairStyle) -> str:
    """File stem of the template for a hair style."""
    return f"hair_{style}"


def _require(template: GridTemplate, parts: frozenset[PartId]) -> None:
    if template.parts != parts:
        raise TemplateError(
            f"{template.name} must paint exactly {sorted(parts)}, got {sorted(template.parts)}"
        )


def _inks(palette: Palette) -> Mapping[str, tuple[int, int, int, int]]:
    inks: dict[str, tuple[int, int, int, int]] = {}
    for symbol, ink in SYMBOLS.items():
        base = palette.of(ink.role)
        color = darken(base) if ink.shade else base
        inks[symbol] = (color.r, color.g, color.b, OPAQUE)
    return inks


def _paint(rows: tuple[str, ...], inks: Mapping[str, tuple[int, int, int, int]]) -> Pixels:
    return np.array([[inks[symbol] for symbol in row] for row in rows], dtype=np.uint8)


class TemplateStylizer:
    """Deterministic stylizer: equal specs give byte-identical skins."""

    def __init__(self, hair: Mapping[HairStyle, GridTemplate], outfit: GridTemplate) -> None:
        missing = [style for style in HAIR_STYLES if style not in hair]
        if missing:
            raise TemplateError(f"missing hair templates: {missing}")
        for template in hair.values():
            _require(template, HAIR_PARTS)
        _require(outfit, OUTFIT_PARTS)
        self._hair = MappingProxyType(dict(hair))
        self._outfit = outfit

    @classmethod
    def from_templates(cls, templates: Mapping[str, GridTemplate]) -> "TemplateStylizer":
        """Pick the hair and outfit templates out of a loaded template directory."""
        try:
            hair = {style: templates[hair_template_name(style)] for style in HAIR_STYLES}
            outfit = templates[OUTFIT_TEMPLATE]
        except KeyError as exc:
            raise TemplateError(f"missing template {exc.args[0]}.grid") from exc
        return cls(hair, outfit)

    def render(self, spec: SkinSpec) -> Skin:
        """Paint every base face; the overlay layer stays transparent."""
        inks = _inks(spec.palette)
        skin = Skin(np.zeros((SKIN_SIZE, SKIN_SIZE, 4), dtype=np.uint8))
        for part in PART_IDS:
            template = self._hair[spec.hair_style] if part in HAIR_PARTS else self._outfit
            for face in FACE_IDS:
                pixels = _paint(template.rows(part, face, spec.model), inks)
                skin = skin.with_face(part, face, pixels, model=spec.model)
        return skin
