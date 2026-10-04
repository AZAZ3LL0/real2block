"""Skin import: validation, 64x32 to 64x64 conversion, slim detection."""

from dataclasses import dataclass
from typing import Literal

import numpy as np

from real2block.domain.errors import WarningCode
from real2block.domain.skin.geometry import (
    FACE_IDS,
    LEGACY_HEIGHT,
    LEGACY_MIRRORS,
    SKIN_SIZE,
    SLIM_PROBE_COLUMNS,
    SLIM_PROBE_PIXEL,
    SLIM_PROBE_ROWS,
    FaceId,
    Model,
    face_rect,
)
from real2block.domain.skin.skin import Pixels, Skin
from real2block.domain.vision.loader import load_skin_png

ModelChoice = Literal["classic", "slim", "auto"]

_SWAPPED_FACES: dict[FaceId, FaceId] = {"right": "left", "left": "right"}


@dataclass(frozen=True, slots=True)
class NormalizedSkin:
    """Imported skin in 64x64 form with its resolved model."""

    skin: Skin
    model: Model
    warnings: tuple[WarningCode, ...]


def convert_legacy(pixels: Pixels) -> Pixels:
    """Expand a 64x32 skin: copy it and mirror right limbs into the left ones."""
    out = np.zeros((SKIN_SIZE, SKIN_SIZE, 4), dtype=np.uint8)
    out[:LEGACY_HEIGHT] = pixels[:LEGACY_HEIGHT]
    for target, source in LEGACY_MIRRORS.items():
        for face in FACE_IDS:
            src = face_rect(source, _SWAPPED_FACES.get(face, face))
            dst = face_rect(target, face)
            region = out[src.y : src.y + src.h, src.x : src.x + src.w]
            out[dst.y : dst.y + dst.h, dst.x : dst.x + dst.w] = np.fliplr(region)
    return out


def detect_model(pixels: Pixels) -> Model:
    """Slim if the probe pixel and probe columns are fully transparent."""
    px, py = SLIM_PROBE_PIXEL
    probe = pixels[
        SLIM_PROBE_ROWS.start : SLIM_PROBE_ROWS.stop,
        SLIM_PROBE_COLUMNS.start : SLIM_PROBE_COLUMNS.stop,
        3,
    ]
    return "slim" if pixels[py, px, 3] == 0 and not probe.any() else "classic"


def resolve_model(skin: Skin, choice: ModelChoice) -> Model:
    """Apply an explicit model choice or detect it."""
    return detect_model(skin.pixels) if choice == "auto" else choice


def normalize_skin(data: bytes) -> NormalizedSkin:
    """Load an uploaded skin, convert legacy layout and detect the model."""
    pixels = load_skin_png(data)
    if pixels.shape[0] == LEGACY_HEIGHT:
        pixels = convert_legacy(pixels)
    skin = Skin(pixels)
    model = detect_model(pixels)
    filled = skin.flatten_overlay(model).fill_transparent_base(model).filled
    warnings: tuple[WarningCode, ...] = ("TRANSPARENT_BASE_PIXELS",) if filled else ()
    return NormalizedSkin(skin, model, warnings)


def load_print_skin(data: bytes) -> Skin:
    """Load a skin for printing; only the 64x64 layout is accepted."""
    return Skin(load_skin_png(data, frozenset({(SKIN_SIZE, SKIN_SIZE)})))
