"""Skin rules from tech.md §4.1: flattening, transparent fill, legacy, slim detection."""

import numpy as np
import pytest

from real2block.domain.color import Rgb
from real2block.domain.skin.geometry import FACE_IDS, PART_IDS, FaceId, Model, face_rect
from real2block.domain.skin.io import convert_legacy, detect_model, normalize_skin
from real2block.domain.skin.skin import Skin
from tests.helpers import blank, png_bytes

RED = (200, 10, 10, 255)
BLUE = (10, 10, 200, 255)


def _opaque_base(model: Model = "classic") -> np.ndarray:
    pixels = blank()
    for part in PART_IDS:
        for face in FACE_IDS:
            r = face_rect(part, face, "base", model)
            pixels[r.y : r.y + r.h, r.x : r.x + r.w] = RED
    return pixels


def test_overlay_replaces_base_only_when_alpha_at_least_128() -> None:
    pixels = _opaque_base()
    over = face_rect("head", "front", "overlay")
    pixels[over.y, over.x] = (*BLUE[:3], 128)
    pixels[over.y, over.x + 1] = (*BLUE[:3], 127)
    flat = Skin(pixels).flatten_overlay("classic")
    base = face_rect("head", "front")
    assert tuple(flat.pixels[base.y, base.x]) == (*BLUE[:3], 128)
    assert tuple(flat.pixels[base.y, base.x + 1]) == RED
    assert not flat.face("head", "front", "overlay").any()


def test_transparent_base_filled_with_gray() -> None:
    pixels = _opaque_base()
    base = face_rect("body", "back")
    pixels[base.y, base.x] = (0, 0, 0, 0)
    pixels[base.y, base.x + 1] = (5, 5, 5, 127)
    result = Skin(pixels).fill_transparent_base("classic")
    assert result.filled == 2
    assert result.skin.rgb_at(base.x, base.y) == Rgb.from_hex("#7F7F7F")
    assert result.skin.pixels[base.y, base.x + 1, 3] == 255


def test_legacy_left_limbs_mirror_right_with_side_swap() -> None:
    legacy = _opaque_base()[:32].copy()
    legacy[16:32, 40:56] = np.random.default_rng(1).integers(0, 255, (16, 16, 4), dtype=np.uint8)
    out = Skin(convert_legacy(legacy))
    np.testing.assert_array_equal(out.pixels[:32], legacy)
    src = Skin(np.vstack([legacy, blank(64, 32)]))
    swap: dict[FaceId, FaceId] = {"right": "left", "left": "right"}
    for face in FACE_IDS:
        expected = np.fliplr(src.face("right_arm", swap.get(face, face)))
        np.testing.assert_array_equal(out.face("left_arm", face), expected)


@pytest.mark.parametrize("model", ["classic", "slim"])
def test_detect_model(model: Model) -> None:
    assert detect_model(_opaque_base(model)) == model


def test_normalize_legacy_png_becomes_64x64() -> None:
    result = normalize_skin(png_bytes(_opaque_base()[:32].copy()))
    assert result.skin.pixels.shape == (64, 64, 4)
    assert result.model == "classic"
    assert result.warnings == ()


def test_normalize_warns_about_transparent_base() -> None:
    result = normalize_skin(png_bytes(blank()))
    assert result.warnings == ("TRANSPARENT_BASE_PIXELS",)


def test_png_encoding_is_deterministic() -> None:
    pixels = _opaque_base()
    assert Skin(pixels).to_png() == Skin(pixels.copy()).to_png()
