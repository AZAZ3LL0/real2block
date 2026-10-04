"""Palette roles and the `.grid` symbol alphabet (tech.md §4.4)."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, get_args

PaletteRole = Literal["skin", "hair", "eye_white", "iris", "mouth", "shirt", "pants", "shoes"]
PALETTE_ROLES: tuple[PaletteRole, ...] = get_args(PaletteRole)


@dataclass(frozen=True, slots=True)
class Ink:
    """What a template cell is painted with: a palette role or its shade."""

    role: PaletteRole
    shade: bool = False


TRANSPARENT_SYMBOL = "."
"""Transparent cell, allowed only on an overlay layer."""

SYMBOLS: Mapping[str, Ink] = MappingProxyType(
    {
        "S": Ink("skin"),
        "s": Ink("skin", shade=True),
        "H": Ink("hair"),
        "h": Ink("hair", shade=True),
        "W": Ink("eye_white"),
        "I": Ink("iris"),
        "M": Ink("mouth"),
        "m": Ink("mouth", shade=True),
        "T": Ink("shirt"),
        "t": Ink("shirt", shade=True),
        "P": Ink("pants"),
        "p": Ink("pants", shade=True),
        "F": Ink("shoes"),
        "f": Ink("shoes", shade=True),
    }
)
