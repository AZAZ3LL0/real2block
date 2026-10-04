"""Color value object; hex strings exist only at the API boundary."""

import math
import re
from dataclasses import dataclass

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# CIE Lab relative to the sRGB D65 white point.
_WHITE = (0.95047, 1.0, 1.08883)
_RGB_TO_XYZ = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)
_XYZ_TO_RGB = (
    (3.2404542, -1.5371385, -0.4985314),
    (-0.9692660, 1.8760108, 0.0415560),
    (0.0556434, -0.2040259, 1.0572252),
)
_EPSILON = 216 / 24389
_KAPPA = 24389 / 27
SRGB_LINEAR_CUTOFF = 0.04045
SHADE_DELTA_L = 12.0
"""Lightness drop of a role shade (tech.md §4.4)."""


@dataclass(frozen=True, slots=True)
class Rgb:
    """Opaque 8-bit RGB color."""

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for channel in (self.r, self.g, self.b):
            if not 0 <= channel <= 255:
                raise ValueError(f"channel out of range: {channel}")

    @classmethod
    def from_hex(cls, value: str) -> "Rgb":
        """Parse `#RRGGBB` (case-insensitive)."""
        if not _HEX_RE.match(value):
            raise ValueError(f"invalid hex color: {value!r}")
        return cls(int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))

    def to_hex(self) -> str:
        """Format as upper-case `#RRGGBB`."""
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"


@dataclass(frozen=True, slots=True)
class Lab:
    """CIE L*a*b* color, D65 white point."""

    l: float  # noqa: E741 - the standard name of the lightness channel
    a: float
    b: float

    def to_rgb(self) -> Rgb:
        """Nearest 8-bit sRGB color; out-of-gamut channels are clipped."""
        fy = (self.l + 16) / 116
        fx = fy + self.a / 500
        fz = fy - self.b / 200
        xyz = [w * _f_inv(f) for w, f in zip(_WHITE, (fx, fy, fz), strict=True)]
        channels = [_encode(_dot(row, xyz)) for row in _XYZ_TO_RGB]
        return Rgb(*channels)


def _dot(row: tuple[float, float, float], vec: list[float]) -> float:
    return sum(m * v for m, v in zip(row, vec, strict=True))


def _decode(channel: int) -> float:
    c = channel / 255
    return c / 12.92 if c <= SRGB_LINEAR_CUTOFF else ((c + 0.055) / 1.055) ** 2.4


def _encode(linear: float) -> int:
    c = min(1.0, max(0.0, linear))
    c = 12.92 * c if c <= SRGB_LINEAR_CUTOFF / 12.92 else 1.055 * c ** (1 / 2.4) - 0.055
    return round(c * 255)


def _f(t: float) -> float:
    return math.cbrt(t) if t > _EPSILON else (_KAPPA * t + 16) / 116


def _f_inv(f: float) -> float:
    cube = f**3
    return cube if cube > _EPSILON else (116 * f - 16) / _KAPPA


def to_lab(color: Rgb) -> Lab:
    """Convert an sRGB color to Lab."""
    linear = [_decode(c) for c in (color.r, color.g, color.b)]
    fx, fy, fz = (_f(_dot(row, linear) / w) for row, w in zip(_RGB_TO_XYZ, _WHITE, strict=True))
    return Lab(116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(first: Rgb, second: Rgb) -> float:
    """CIE76 color difference."""
    p, q = to_lab(first), to_lab(second)
    return math.dist((p.l, p.a, p.b), (q.l, q.a, q.b))


def darken(color: Rgb, delta_l: float = SHADE_DELTA_L) -> Rgb:
    """Same hue with lightness lowered by `delta_l`, clamped at black."""
    lab = to_lab(color)
    return Lab(max(0.0, lab.l - delta_l), lab.a, lab.b).to_rgb()


TRANSPARENT_FILL = Rgb(0x7F, 0x7F, 0x7F)
"""Replacement for base pixels left transparent after flattening (tech.md §4.1)."""
