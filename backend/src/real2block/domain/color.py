"""Color value object, Lab conversion and palette quantization.

Hex strings exist only at the API boundary.
"""

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np
import numpy.typing as npt

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

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


TRANSPARENT_FILL = Rgb(0x7F, 0x7F, 0x7F)
"""Replacement for base pixels left transparent after flattening (tech.md §4.1)."""


QUANTIZE_SEED = 1729
"""Fixed k-means seed: equal skins must give equal palettes (tech.md §4.5)."""
QUANTIZE_ATTEMPTS = 3
_KMEANS_CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.1)


def to_lab(colors: Sequence[Rgb]) -> npt.NDArray[np.float32]:
    """CIE Lab (D65) of each color as an (n, 3) array; L in 0..100."""
    rgb = np.array([[(c.r, c.g, c.b) for c in colors]], dtype=np.float32) / 255
    lab: npt.NDArray[np.float32] = cv2.cvtColor(rgb, cv2.COLOR_RGB2Lab)[0]
    return lab


def quantize(samples: Sequence[Rgb], max_colors: int) -> dict[Rgb, Rgb]:
    """Map every sampled color to one of at most `max_colors` representatives.

    Clusters come from k-means in Lab over all samples, so frequent colors weigh more.
    Each cluster is represented by its most frequent member, which keeps exact colors
    of large areas instead of averaged ones.
    """
    counts = Counter(samples)
    unique = sorted(counts, key=lambda c: (c.r, c.g, c.b))
    if len(unique) <= max_colors:
        return {c: c for c in unique}
    data = to_lab(samples)
    cv2.setRNGSeed(QUANTIZE_SEED)
    # Initial labels are ignored with k-means++ seeding; the stubs require an array.
    initial = np.zeros((len(samples), 1), dtype=np.int32)
    _, labels, _ = cv2.kmeans(
        data, max_colors, initial, _KMEANS_CRITERIA, QUANTIZE_ATTEMPTS, cv2.KMEANS_PP_CENTERS
    )
    flat = np.asarray(labels).ravel()
    cluster_of = {color: int(label) for color, label in zip(samples, flat, strict=True)}
    members: dict[int, list[Rgb]] = {}
    for color in unique:
        members.setdefault(cluster_of[color], []).append(color)
    mapping: dict[Rgb, Rgb] = {}
    for group in members.values():
        representative = max(group, key=lambda c: (counts[c], -c.r, -c.g, -c.b))
        mapping.update({c: representative for c in group})
    return mapping


def pixels_to_lab(pixels: npt.NDArray[np.uint8]) -> npt.NDArray[np.float32]:
    """CIE Lab (D65) of 8-bit RGB pixels of any shape, flattened to (n, 3)."""
    rgb = pixels.reshape(1, -1, 3).astype(np.float32) / 255
    lab: npt.NDArray[np.float32] = cv2.cvtColor(rgb, cv2.COLOR_RGB2Lab)[0]
    return lab


def from_lab(lab: npt.NDArray[np.float32]) -> Rgb:
    """Nearest 8-bit color of one Lab triple; out-of-gamut channels are clipped."""
    rgb = cv2.cvtColor(lab.reshape(1, 1, 3).astype(np.float32), cv2.COLOR_Lab2RGB)[0, 0]
    r, g, b = (round(min(1.0, max(0.0, float(c))) * 255) for c in rgb)
    return Rgb(r, g, b)


def delta_e(a: npt.NDArray[np.float32], b: npt.NDArray[np.float32]) -> float:
    """CIE76 color difference of two Lab triples."""
    return float(np.linalg.norm(a.astype(np.float64) - b.astype(np.float64)))


def darken(color: Rgb, delta_l: float = SHADE_DELTA_L) -> Rgb:
    """Same a and b in Lab with lightness lowered by `delta_l`, clamped at black.

    Out-of-gamut results are clipped per channel.
    """
    lab = to_lab([color])[0]
    lab[0] = max(0.0, float(lab[0]) - delta_l)
    return from_lab(lab)
