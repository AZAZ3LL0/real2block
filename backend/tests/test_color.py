"""Role shades (tech.md §4.4: shade = darken(base, dL=12) in Lab)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from real2block.domain.color import Rgb, darken, to_lab

channels = st.integers(min_value=0, max_value=255)
colors = st.builds(Rgb, channels, channels, channels)

# Defaults of the shaded roles from tech.md §5.1 plus typical skin tones.
ROLE_COLORS = ["#2E3A8C", "#3A3A3A", "#3FA7A0", "#9C5B4E", "#4A3222"]
SKIN_TONES = ["#F1C27D", "#E0AC69", "#C68642", "#8D5524", "#FFDBAC"]


def lab(color: Rgb) -> tuple[float, float, float]:
    l_, a, b = (float(v) for v in to_lab([color])[0])
    return l_, a, b


@given(colors)
def test_zero_darkening_keeps_the_color(color: Rgb) -> None:
    same = darken(color, 0.0)
    # The float32 Lab round trip may land one 8-bit step away in very dark colors.
    assert max(abs(same.r - color.r), abs(same.g - color.g), abs(same.b - color.b)) <= 1


@pytest.mark.parametrize("hex_color", ROLE_COLORS + SKIN_TONES)
def test_darken_lowers_lightness_by_twelve(hex_color: str) -> None:
    color = Rgb.from_hex(hex_color)
    (l0, a0, b0), (l1, a1, b1) = lab(color), lab(darken(color))
    # Only 8-bit rounding separates the result from the exact Lab target.
    assert l1 == pytest.approx(l0 - 12.0, abs=0.5)
    assert (a1, b1) == pytest.approx((a0, b0), abs=1.5)


@given(st.integers(min_value=0, max_value=255))
def test_darken_gray_is_exact_in_lightness(level: int) -> None:
    gray = Rgb(level, level, level)
    expected = max(0.0, lab(gray)[0] - 12.0)
    assert lab(darken(gray))[0] == pytest.approx(expected, abs=0.5)


@given(colors)
def test_darken_never_lightens(color: Rgb) -> None:
    assert lab(darken(color))[0] <= lab(color)[0] + 0.5


def test_darken_clamps_at_black() -> None:
    assert darken(Rgb(10, 10, 10)) == Rgb(0, 0, 0)


def test_darken_keeps_neutral_gray_neutral() -> None:
    shade = darken(Rgb(128, 128, 128))
    assert shade.r == shade.g == shade.b
