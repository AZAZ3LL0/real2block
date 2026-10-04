"""Immutable 64x64 RGBA skin with face access and overlay flattening."""

import io
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from PIL import Image

from blockfold.domain.color import TRANSPARENT_FILL, Rgb
from blockfold.domain.skin.geometry import (
    FACE_IDS,
    PART_IDS,
    SKIN_SIZE,
    FaceId,
    Layer,
    Model,
    PartId,
    Rect,
    face_rect,
)

Pixels = npt.NDArray[np.uint8]

OPAQUE_ALPHA = 128
"""Alpha at or above which a pixel counts as opaque (tech.md §4.1)."""


def _region(pixels: Pixels, rect: Rect) -> Pixels:
    return pixels[rect.y : rect.y + rect.h, rect.x : rect.x + rect.w]


@dataclass(frozen=True, slots=True)
class FillResult:
    """Skin with opaque base and the number of pixels that had to be filled."""

    skin: "Skin"
    filled: int


class Skin:
    """Read-only RGBA texture of a 64x64 skin."""

    __slots__ = ("_pixels",)

    def __init__(self, pixels: Pixels) -> None:
        if pixels.shape != (SKIN_SIZE, SKIN_SIZE, 4) or pixels.dtype != np.uint8:
            raise ValueError(f"expected uint8 array of shape 64x64x4, got {pixels.shape}")
        own = pixels.copy()
        own.flags.writeable = False
        self._pixels = own

    @property
    def pixels(self) -> Pixels:
        """Read-only pixel array, shape (64, 64, 4)."""
        return self._pixels

    def face(
        self, part: PartId, face: FaceId, layer: Layer = "base", model: Model = "classic"
    ) -> Pixels:
        """Pixels of one face as (h, w, 4), in texture orientation."""
        return _region(self._pixels, face_rect(part, face, layer, model))

    def rgb_at(self, x: int, y: int) -> Rgb:
        """Color of one texture pixel, alpha ignored."""
        r, g, b, _ = (int(c) for c in self._pixels[y, x])
        return Rgb(r, g, b)

    def flatten_overlay(self, model: Model) -> "Skin":
        """Merge overlay into base where overlay alpha >= 128; overlay is cleared."""
        out = self._pixels.copy()
        for part in PART_IDS:
            for face in FACE_IDS:
                base = _region(out, face_rect(part, face, "base", model))
                over = _region(self._pixels, face_rect(part, face, "overlay", model))
                mask = over[..., 3] >= OPAQUE_ALPHA
                base[mask] = over[mask]
        for part in PART_IDS:
            for face in FACE_IDS:
                _region(out, face_rect(part, face, "overlay", model))[...] = 0
        return Skin(out)

    def fill_transparent_base(self, model: Model) -> FillResult:
        """Replace base pixels with alpha < 128 by the neutral gray fill."""
        out = self._pixels.copy()
        fill = np.array([TRANSPARENT_FILL.r, TRANSPARENT_FILL.g, TRANSPARENT_FILL.b, 255])
        filled = 0
        for part in PART_IDS:
            for face in FACE_IDS:
                base = _region(out, face_rect(part, face, "base", model))
                mask = base[..., 3] < OPAQUE_ALPHA
                filled += int(mask.sum())
                base[mask] = fill
        return FillResult(Skin(out), filled)

    def to_png(self) -> bytes:
        """Encode as RGBA PNG without metadata; deterministic for equal pixels."""
        buf = io.BytesIO()
        Image.fromarray(np.asarray(self._pixels)).save(buf, format="PNG")
        return buf.getvalue()
