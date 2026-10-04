"""Palette reduction and color legend from tech.md §4.5 and §5.5."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from real2block.domain.color import Rgb, quantize, to_lab
from real2block.domain.papercraft.legend import build_legend, cell_colors, prepare_skin
from real2block.domain.skin.skin import Skin

TOTAL_CELLS = 1632  # sum of 2(wh + wd + hd) over the six classic boxes

channels = st.integers(min_value=0, max_value=255)
colors = st.builds(Rgb, channels, channels, channels)


def test_lab_of_reference_colors() -> None:
    white, black, red = to_lab([Rgb(255, 255, 255), Rgb(0, 0, 0), Rgb(255, 0, 0)])
    assert white == pytest.approx([100, 0, 0], abs=0.5)
    assert black == pytest.approx([0, 0, 0], abs=0.5)
    assert red == pytest.approx([53.2, 80.1, 67.2], abs=0.5)


def test_sixteen_colors_are_kept() -> None:
    palette = [Rgb(i * 16, 255 - i * 16, i) for i in range(16)]
    samples = palette * 3
    assert quantize(samples, 16) == {c: c for c in palette}


@settings(max_examples=40, deadline=None)
@given(st.lists(colors, min_size=17, max_size=300))
def test_at_most_sixteen_representatives_from_input(samples: list[Rgb]) -> None:
    mapping = quantize(samples, 16)
    assert set(mapping) == set(samples)
    assert len(set(mapping.values())) <= 16
    assert set(mapping.values()) <= set(samples)


def test_near_duplicates_merge_and_distinct_colors_stay() -> None:
    distinct = [Rgb(r, g, b) for r in (0, 255) for g in (0, 128, 255) for b in (0, 255)]
    distinct += [Rgb(128, 128, 128), Rgb(64, 32, 200), Rgb(200, 64, 32), Rgb(32, 200, 64)]
    near = Rgb(1, 0, 0)
    samples = [*distinct * 5, near]
    mapping = quantize(samples, 16)
    assert mapping[near] == Rgb(0, 0, 0)
    assert all(mapping[c] == c for c in distinct)


def test_quantize_is_deterministic_across_threads() -> None:
    samples = [Rgb(i * 7 % 256, i * 13 % 256, i * 29 % 256) for i in range(200)]
    expected = quantize(samples, 16)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: quantize(samples, 16), range(8)))
    assert all(result == expected for result in results)


def test_numbers_follow_decreasing_cell_count() -> None:
    samples = [Rgb(1, 1, 1)] * 2 + [Rgb(2, 2, 2)] * 5 + [Rgb(3, 3, 3)] * 3
    legend = build_legend(samples, "numbered")
    assert [(e.number, e.color, e.cells) for e in legend.entries] == [
        (1, Rgb(2, 2, 2), 5),
        (2, Rgb(3, 3, 3), 3),
        (3, Rgb(1, 1, 1), 2),
    ]
    assert legend.number_of(Rgb(3, 3, 3)) == 2
    assert legend.number_of(Rgb(9, 9, 9)) is None


def test_color_legend_keeps_32_and_sums_the_rest() -> None:
    samples = [Rgb(i, 0, 0) for i in range(40) for _ in range(100 - i)]
    legend = build_legend(samples, "color")
    assert len(legend.entries) == 32
    assert legend.entries[-1].color == Rgb(31, 0, 0)
    assert legend.other_cells == sum(100 - i for i in range(32, 40))


def test_numbered_reference_skin_is_reduced(reference_skin: Skin) -> None:
    assert len(set(cell_colors(reference_skin, "classic"))) > 16
    prepared = prepare_skin(reference_skin, "classic", "numbered")
    printed = cell_colors(prepared.skin, "classic")
    assert prepared.reduced
    assert len(set(printed)) <= 16
    assert {e.color for e in prepared.legend.entries} == set(printed)
    assert sum(e.cells for e in prepared.legend.entries) == TOTAL_CELLS
    assert prepared.legend.other_cells == 0


def test_color_mode_keeps_skin(reference_skin: Skin) -> None:
    prepared = prepare_skin(reference_skin, "classic", "color")
    assert not prepared.reduced
    assert prepared.skin is reference_skin
    legend = prepared.legend
    assert len(legend.entries) == 32
    assert sum(e.cells for e in legend.entries) + legend.other_cells == TOTAL_CELLS


def test_numbered_skin_with_few_colors_is_not_reduced(reference_skin: Skin) -> None:
    pixels = reference_skin.pixels.copy()
    pixels[..., :3] = 200
    prepared = prepare_skin(Skin(pixels), "classic", "numbered")
    assert not prepared.reduced
    assert [(e.number, e.cells) for e in prepared.legend.entries] == [(1, TOTAL_CELLS)]
