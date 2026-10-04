"""Lab conversion and role shades (tech.md §4.4: shade = darken(base, dL=12) in Lab)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from real2block.domain.color import Rgb, darken, delta_e, to_lab

channels = st.integers(min_value=0, max_value=255)
colors = st.builds(Rgb, channels, channels, channels)


@pytest.mark.parametrize(
    ("color", "lab"),
    [
        (Rgb(255, 255, 255), (100.0, 0.0, 0.0)),
        (Rgb(0, 0, 0), (0.0, 0.0, 0.0)),
        (Rgb(255, 0, 0), (53.24, 80.09, 67.20)),
        (Rgb(0, 0, 255), (32.30, 79.19, -107.86)),
        (Rgb(128, 128, 128), (53.59, 0.0, 0.0)),
    ],
)
def test_known_lab_values(color: Rgb, lab: tuple[float, float, float]) -> None:
    got = to_lab(color)
    assert (got.l, got.a, got.b) == pytest.approx(lab, abs=0.01)


@given(colors)
def test_lab_round_trip_is_exact(color: Rgb) -> None:
    assert to_lab(color).to_rgb() == color


# Defaults of the shaded roles from tech.md §5.1 plus typical skin tones.
ROLE_COLORS = ["#2E3A8C", "#3A3A3A", "#3FA7A0", "#9C5B4E", "#4A3222"]
SKIN_TONES = ["#F1C27D", "#E0AC69", "#C68642", "#8D5524", "#FFDBAC"]


@pytest.mark.parametrize("hex_color", ROLE_COLORS + SKIN_TONES)
def test_darken_lowers_lightness_by_twelve(hex_color: str) -> None:
    color = Rgb.from_hex(hex_color)
    before, after = to_lab(color), to_lab(darken(color))
    # Only 8-bit rounding separates the result from the exact Lab target.
    assert after.l == pytest.approx(before.l - 12.0, abs=0.5)
    assert (after.a, after.b) == pytest.approx((before.a, before.b), abs=1.5)


@given(st.integers(min_value=0, max_value=255))
def test_darken_gray_is_exact_in_lightness(level: int) -> None:
    gray = Rgb(level, level, level)
    expected = max(0.0, to_lab(gray).l - 12.0)
    assert to_lab(darken(gray)).l == pytest.approx(expected, abs=0.5)


@given(colors)
def test_darken_never_lightens(color: Rgb) -> None:
    assert to_lab(darken(color)).l <= to_lab(color).l + 1e-9


def test_darken_clamps_at_black() -> None:
    assert darken(Rgb(10, 10, 10)) == Rgb(0, 0, 0)


def test_darken_keeps_neutral_gray_neutral() -> None:
    shade = darken(Rgb(128, 128, 128))
    assert shade.r == shade.g == shade.b


def test_delta_e() -> None:
    assert delta_e(Rgb(1, 2, 3), Rgb(1, 2, 3)) == 0.0
    assert delta_e(Rgb(0, 0, 0), Rgb(255, 255, 255)) == pytest.approx(100.0, abs=0.01)
