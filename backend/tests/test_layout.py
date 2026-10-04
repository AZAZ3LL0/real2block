"""Page layout from tech.md §4.3: shelf packing, bounds, gaps and the A4 reference case."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from real2block.domain.errors import InvalidOptionsError
from real2block.domain.papercraft.layout import NetPage, Paper, layout_pages
from real2block.domain.papercraft.net import NetPart, build_net_part
from real2block.domain.skin.geometry import PART_IDS, Model
from real2block.domain.skin.skin import Skin

PAPER_MM: dict[Paper, tuple[float, float]] = {"A4": (210.0, 297.0), "Letter": (215.9, 279.4)}
MARGIN = 10.0
HEADER = 12.0
GAP = 8.0
TAB = 6.0
HEAD_CELLS = 32
EPS = 1e-6

papers = st.sampled_from(list(PAPER_MM))
models = st.sampled_from(["classic", "slim"])
pixel_sizes = st.floats(min_value=3.0, max_value=8.0, allow_nan=False)


def _nets(skin: Skin, model: Model, pixel_mm: float) -> list[NetPart]:
    return [build_net_part(skin, part, model, pixel_mm) for part in PART_IDS]


def _head_fits(paper: Paper, pixel_mm: float) -> bool:
    # The widest net is the head: 2d + 2w = 32 cells plus the back seam tab.
    width, _ = PAPER_MM[paper]
    return HEAD_CELLS * pixel_mm + TAB <= width - 2 * MARGIN


def _boxes(page: NetPage) -> list[tuple[float, float, float, float]]:
    return [(p.x, p.y, p.x + p.net.width, p.y + p.net.height) for p in page.placements]


@settings(max_examples=60, deadline=None)
@given(papers, models, pixel_sizes)
def test_parts_inside_printable_area_and_apart(
    reference_skin: Skin, paper: Paper, model: Model, pixel_mm: float
) -> None:
    if not _head_fits(paper, pixel_mm):
        return
    pages = layout_pages(_nets(reference_skin, model, pixel_mm), paper)
    width, height = PAPER_MM[paper]
    for page in pages:
        assert (page.frame.width, page.frame.height) == (width, height)
        boxes = _boxes(page)
        for x0, y0, x1, y1 in boxes:
            assert x0 >= MARGIN - EPS
            assert y0 >= MARGIN + HEADER - EPS
            assert x1 <= width - MARGIN + EPS
            assert y1 <= height - MARGIN + EPS
        for i, a in enumerate(boxes):
            for b in boxes[i + 1 :]:
                apart_x = max(a[0], b[0]) - min(a[2], b[2])
                apart_y = max(a[1], b[1]) - min(a[3], b[3])
                assert max(apart_x, apart_y) >= GAP - EPS


@settings(max_examples=60, deadline=None)
@given(papers, models, pixel_sizes)
def test_every_part_placed_once_unrotated(
    reference_skin: Skin, paper: Paper, model: Model, pixel_mm: float
) -> None:
    if not _head_fits(paper, pixel_mm):
        return
    nets = _nets(reference_skin, model, pixel_mm)
    pages = layout_pages(nets, paper)
    placed = [p.net for page in pages for p in page.placements]
    assert [n.part for n in placed] == list(PART_IDS)
    for net, original in zip(placed, nets, strict=True):
        assert (net.width, net.height) == (original.width, original.height)


def test_a4_5mm_classic_reference(reference_skin: Skin) -> None:
    pages = layout_pages(_nets(reference_skin, "classic", 5.0), "A4")
    assert len(pages) == 2
    first = [(p.net.part, p.net.width, p.net.height) for p in pages[0].placements]
    assert first == [("head", 166.0, 132.0), ("body", 126.0, 112.0)]
    second = pages[1].placements
    assert [p.net.part for p in second] == ["right_arm", "left_arm", "right_leg", "left_leg"]
    assert all((p.net.width, p.net.height) == (86.0, 112.0) for p in second)
    # 2x2 grid: two columns, two rows.
    assert len({p.x for p in second}) == 2
    assert len({p.y for p in second}) == 2


def test_letter_5mm_classic(reference_skin: Skin) -> None:
    # Letter content is 247.4 mm tall: head (132) + gap + body (112) no longer fit.
    pages = layout_pages(_nets(reference_skin, "classic", 5.0), "Letter")
    parts = [[p.net.part for p in page.placements] for page in pages]
    assert parts == [["head"], ["body", "right_arm", "left_arm"], ["right_leg", "left_leg"]]


def test_small_cells_share_pages(reference_skin: Skin) -> None:
    pages = layout_pages(_nets(reference_skin, "classic", 3.0), "A4")
    assert len(pages) == 1


@pytest.mark.parametrize("paper", ["A4", "Letter"])
def test_net_wider_than_page_is_rejected(reference_skin: Skin, paper: Paper) -> None:
    with pytest.raises(InvalidOptionsError):
        layout_pages(_nets(reference_skin, "classic", 8.0), paper)
