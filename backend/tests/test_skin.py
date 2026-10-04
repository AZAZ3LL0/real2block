"""Skin rules from tech.md §4.1: flattening, transparent fill, legacy, slim detection."""

import io

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from PIL import Image

from real2block.domain.color import Rgb
from real2block.domain.skin.geometry import (
    FACE_IDS,
    LAYERS,
    PART_IDS,
    SLIM_PROBE_COLUMNS,
    SLIM_PROBE_PIXEL,
    SLIM_PROBE_ROWS,
    FaceId,
    Model,
    PartId,
    face_rect,
)
from real2block.domain.skin.io import convert_legacy, detect_model, normalize_skin, resolve_model
from real2block.domain.skin.skin import OPAQUE_ALPHA, Skin
from tests.helpers import blank, png_bytes

RED = (200, 10, 10, 255)
BLUE = (10, 10, 200, 255)
GRAY_FILL = (0x7F, 0x7F, 0x7F, 255)
MODELS: tuple[Model, ...] = ("classic", "slim")
LEGACY_LIMBS: tuple[tuple[PartId, PartId], ...] = (
    ("left_arm", "right_arm"),
    ("left_leg", "right_leg"),
)


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


# Skin face access (tech.md §3: get/put faces)


def test_with_face_replaces_only_that_face() -> None:
    pixels = _opaque_base("slim")
    original = Skin(pixels)
    rect = face_rect("left_arm", "back", "overlay", "slim")
    patch = np.full((rect.h, rect.w, 4), BLUE, dtype=np.uint8)
    updated = original.with_face("left_arm", "back", patch, "overlay", "slim")
    np.testing.assert_array_equal(updated.face("left_arm", "back", "overlay", "slim"), patch)
    expected = pixels.copy()
    expected[rect.y : rect.y + rect.h, rect.x : rect.x + rect.w] = BLUE
    np.testing.assert_array_equal(updated.pixels, expected)
    np.testing.assert_array_equal(original.pixels, pixels)


def test_with_face_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError, match="shape"):
        Skin(blank()).with_face("head", "front", np.zeros((8, 7, 4), dtype=np.uint8))


# Flattening and fill for every face of both models (tech.md §4.1)

seeds = st.integers(min_value=0, max_value=2**32 - 1)
models = st.sampled_from(MODELS)


def _random_skin(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, (64, 64, 4), dtype=np.uint8)


def _layer_mask(model: Model) -> np.ndarray:
    mask = np.zeros((64, 64), dtype=bool)
    for layer in LAYERS:
        for part in PART_IDS:
            for face in FACE_IDS:
                r = face_rect(part, face, layer, model)
                mask[r.y : r.y + r.h, r.x : r.x + r.w] = True
    return mask


@settings(max_examples=25, deadline=None)
@given(seeds, models)
def test_flatten_overlay_rule_holds_for_every_face(seed: int, model: Model) -> None:
    source = Skin(_random_skin(seed))
    flat = source.flatten_overlay(model)
    for part in PART_IDS:
        for face in FACE_IDS:
            base = source.face(part, face, "base", model)
            over = source.face(part, face, "overlay", model)
            expected = np.where((over[..., 3] >= OPAQUE_ALPHA)[..., None], over, base)
            np.testing.assert_array_equal(flat.face(part, face, "base", model), expected)
            assert not flat.face(part, face, "overlay", model).any()
    outside = ~_layer_mask(model)
    np.testing.assert_array_equal(flat.pixels[outside], source.pixels[outside])


@settings(max_examples=25, deadline=None)
@given(seeds, models)
def test_fill_makes_every_base_pixel_opaque(seed: int, model: Model) -> None:
    source = Skin(_random_skin(seed))
    result = source.fill_transparent_base(model)
    expected_filled = 0
    for part in PART_IDS:
        for face in FACE_IDS:
            before = source.face(part, face, "base", model)
            after = result.skin.face(part, face, "base", model)
            transparent = before[..., 3] < OPAQUE_ALPHA
            expected_filled += int(transparent.sum())
            assert (after[transparent] == GRAY_FILL).all()
            np.testing.assert_array_equal(after[~transparent], before[~transparent])
            np.testing.assert_array_equal(
                result.skin.face(part, face, "overlay", model),
                source.face(part, face, "overlay", model),
            )
    assert result.filled == expected_filled


def test_opaque_skin_needs_no_fill() -> None:
    assert Skin(_opaque_base("slim")).fill_transparent_base("slim").filled == 0


# Legacy 64x32 conversion (tech.md §4.1)


def test_legacy_conversion_mirrors_both_limbs_and_leaves_rest_empty() -> None:
    legacy = _random_skin(7)[:32].copy()
    out = Skin(convert_legacy(legacy))
    source = Skin(np.vstack([legacy, blank(64, 32)]))
    swap: dict[FaceId, FaceId] = {"right": "left", "left": "right"}
    written = np.zeros((64, 64), dtype=bool)
    written[:32] = True
    for target, mirror in LEGACY_LIMBS:
        for face in FACE_IDS:
            expected = np.fliplr(source.face(mirror, swap.get(face, face)))
            np.testing.assert_array_equal(out.face(target, face), expected)
            r = face_rect(target, face)
            written[r.y : r.y + r.h, r.x : r.x + r.w] = True
    np.testing.assert_array_equal(out.pixels[:32], legacy)
    assert not out.pixels[~written].any()


def test_legacy_front_marker_moves_to_opposite_corner() -> None:
    legacy = _opaque_base()[:32].copy()
    front = face_rect("right_leg", "front")
    legacy[front.y, front.x] = BLUE
    out = Skin(convert_legacy(legacy))
    mirrored = out.face("left_leg", "front")
    assert tuple(mirrored[0, -1]) == BLUE
    assert tuple(mirrored[0, 0]) == RED


# Slim detection probes (tech.md §4.1)


def _slim_probes() -> list[tuple[int, int]]:
    px, py = SLIM_PROBE_PIXEL
    return [(px, py)] + [(x, y) for x in SLIM_PROBE_COLUMNS for y in SLIM_PROBE_ROWS]


@pytest.mark.parametrize("probe", _slim_probes())
def test_any_visible_probe_pixel_means_classic(probe: tuple[int, int]) -> None:
    pixels = _opaque_base("slim")
    x, y = probe
    pixels[y, x] = (0, 0, 0, 1)
    assert detect_model(pixels) == "classic"


def test_transparent_probes_mean_slim_regardless_of_color() -> None:
    pixels = _opaque_base()
    for x, y in _slim_probes():
        pixels[y, x] = (255, 255, 255, 0)
    assert detect_model(pixels) == "slim"


def test_explicit_model_overrides_detection() -> None:
    skin = Skin(_opaque_base("slim"))
    assert resolve_model(skin, "auto") == "slim"
    assert resolve_model(skin, "classic") == "classic"


# Import of ready skins (tech.md §1, §5.4 /skin/normalize)


def test_normalize_keeps_64x64_pixels_unchanged() -> None:
    pixels = _random_skin(3)
    result = normalize_skin(png_bytes(pixels))
    np.testing.assert_array_equal(result.skin.pixels, pixels)


def test_normalize_legacy_keeps_upper_half() -> None:
    legacy = _opaque_base()[:32].copy()
    result = normalize_skin(png_bytes(legacy))
    np.testing.assert_array_equal(result.skin.pixels[:32], legacy)


def test_normalize_detects_slim() -> None:
    assert normalize_skin(png_bytes(_opaque_base("slim"))).model == "slim"


@pytest.mark.parametrize("mode", ["RGB", "L", "LA", "P", "I;16"])
def test_normalize_accepts_any_png_mode(mode: str) -> None:
    img = Image.fromarray(_opaque_base()).convert(mode)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = normalize_skin(buf.getvalue())
    assert result.skin.pixels.shape == (64, 64, 4)


def test_normalize_palette_transparency_becomes_alpha() -> None:
    img = Image.new("P", (64, 64), 0)
    img.putpalette([0, 0, 0, 200, 10, 10])
    head = face_rect("head", "front")
    img.paste(1, (head.x, head.y, head.x + head.w, head.y + head.h))
    buf = io.BytesIO()
    img.save(buf, format="PNG", transparency=0)
    skin = normalize_skin(buf.getvalue()).skin
    assert skin.face("head", "front")[..., 3].min() == 255
    assert skin.pixels[0, 0, 3] == 0
