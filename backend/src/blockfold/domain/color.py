"""Color value object; hex strings exist only at the API boundary."""

import re
from dataclasses import dataclass

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


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
