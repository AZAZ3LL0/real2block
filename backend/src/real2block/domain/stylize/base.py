"""Domain skin spec and the stylizer protocol (tech.md §5.1, §5.3)."""

from dataclasses import dataclass
from typing import Literal, Protocol, get_args

from real2block.domain.color import Rgb
from real2block.domain.skin.geometry import Model
from real2block.domain.skin.skin import Skin
from real2block.domain.stylize.roles import PaletteRole

HairStyle = Literal["short", "long", "bald", "fringe"]
StylizerId = Literal["template", "downsample"]
HAIR_STYLES: tuple[HairStyle, ...] = get_args(HairStyle)


@dataclass(frozen=True, slots=True)
class Palette:
    """Base color of every role; shades are derived, never stored."""

    skin: Rgb
    hair: Rgb
    eye_white: Rgb
    iris: Rgb
    mouth: Rgb
    shirt: Rgb
    pants: Rgb
    shoes: Rgb

    def of(self, role: PaletteRole) -> Rgb:
        """Color of a role."""
        color: Rgb = getattr(self, role)
        return color


@dataclass(frozen=True, slots=True)
class SkinSpec:
    """Domain copy of the API SkinSpec with colors as `Rgb`."""

    model: Model
    stylizer: StylizerId
    hair_style: HairStyle
    palette: Palette
    face_front: tuple[tuple[Rgb, ...], ...] | None = None


class Stylizer(Protocol):
    """Turns a skin spec into a skin."""

    def render(self, spec: SkinSpec) -> Skin:
        """Render the 64x64 skin for the spec."""
        ...
