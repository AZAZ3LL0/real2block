"""Net pages from tech.md §4.2-4.3 and §10.10: line styles, ruler, grid, page sizes."""

import io
from collections import Counter

import pytest
from pypdf import PdfReader

from real2block.domain.papercraft.document import NetDocument
from real2block.domain.papercraft.layout import NetPage, Paper, layout_pages
from real2block.domain.papercraft.net import Segment, build_net_part
from real2block.domain.papercraft.pdf import PdfRenderer
from real2block.domain.skin.geometry import PART_IDS
from real2block.domain.skin.skin import Skin
from tests.helpers import PdfSegment, StrokeStyle, pdf_segments

PT_PER_MM = 72 / 25.4
PAPER_PT: dict[Paper, tuple[float, float]] = {"A4": (595.28, 841.89), "Letter": (612.0, 792.0)}
CUT = (0.6, ())
FOLD = (0.4, (3.0, 2.0))
GRID_WIDTH = 0.1
RULER_TICKS = 6


def _pages(skin: Skin, paper: Paper, pixel_mm: float) -> tuple[NetPage, ...]:
    nets = [build_net_part(skin, part, "classic", pixel_mm) for part in PART_IDS]
    return layout_pages(nets, paper)


def _render(pages: tuple[NetPage, ...], grid: bool = True) -> PdfReader:
    document = NetDocument(pages=pages, lang="en", grid_lines=grid)
    return PdfReader(io.BytesIO(PdfRenderer().render(document)))


def _to_pt(page: NetPage, seg: Segment, dx: float, dy: float) -> PdfSegment:
    a, b = (
        (round((p.x + dx) * PT_PER_MM, 2), round((page.frame.height - p.y - dy) * PT_PER_MM, 2))
        for p in seg
    )
    return (a, b) if a <= b else (b, a)


def _expected(page: NetPage, kind: str) -> Counter[PdfSegment]:
    return Counter(
        _to_pt(page, seg, pl.x, pl.y) for pl in page.placements for seg in getattr(pl.net, kind)
    )


def _drawn(
    drawn: Counter[tuple[StrokeStyle, PdfSegment]], width: float, dash: tuple[float, ...]
) -> Counter[PdfSegment]:
    return Counter(
        {seg: n for (style, seg), n in drawn.items() if (style.width, style.dash) == (width, dash)}
    )


def _close(actual: Counter[PdfSegment], expected: Counter[PdfSegment]) -> bool:
    # Rounding to 0.01 pt can split equal coordinates across a boundary; compare with tolerance.
    remaining = list(actual.elements())
    for seg in expected.elements():
        match = next((s for s in remaining if _near(s, seg)), None)
        if match is None:
            return False
        remaining.remove(match)
    return not remaining


def _near(a: PdfSegment, b: PdfSegment) -> bool:
    return all(
        abs(x - y) <= 0.02 for p, q in zip(a, b, strict=True) for x, y in zip(p, q, strict=True)
    )


@pytest.mark.parametrize(("paper", "pixel_mm"), [("A4", 5.0), ("Letter", 4.0), ("A4", 3.0)])
def test_cut_and_fold_lines_match_nets(reference_skin: Skin, paper: Paper, pixel_mm: float) -> None:
    pages = _pages(reference_skin, paper, pixel_mm)
    reader = _render(pages)
    for index, page in enumerate(pages):
        drawn = pdf_segments(reader, index)
        folds = _drawn(drawn, *FOLD)
        cuts = _drawn(drawn, *CUT)
        assert _close(folds, _expected(page, "fold"))
        ruler = cuts - _expected(page, "cut")
        assert _close(cuts - ruler, _expected(page, "cut"))
        _assert_ruler(ruler)


def _assert_ruler(ruler: Counter[PdfSegment]) -> None:
    lengths = sorted(round(abs(b[0] - a[0]) + abs(b[1] - a[1]), 1) for a, b in ruler.elements())
    assert lengths[-1] == pytest.approx(50 * PT_PER_MM, abs=0.05)
    assert len(lengths) == 1 + RULER_TICKS


@pytest.mark.parametrize("grid", [True, False])
def test_grid_lines_follow_option(reference_skin: Skin, grid: bool) -> None:
    pages = _pages(reference_skin, "A4", 5.0)
    reader = _render(pages, grid=grid)
    for index, page in enumerate(pages):
        drawn = pdf_segments(reader, index)
        lines = [
            seg
            for (style, seg), n in drawn.items()
            for _ in range(n)
            if style.width == GRID_WIDTH and style.alpha_state is not None
        ]
        faces = [f for pl in page.placements for f in pl.net.faces]
        expected = sum(f.cols - 1 + f.rows - 1 for f in faces) if grid else 0
        assert len(lines) == expected
        alpha = reader.pages[index]["/Resources"].get("/ExtGState", {})
        assert any(float(state.get("/CA", 1)) == 0.25 for state in alpha.values()) == grid


@pytest.mark.parametrize("paper", ["A4", "Letter"])
def test_page_size_and_count(reference_skin: Skin, paper: Paper) -> None:
    pages = _pages(reference_skin, paper, 5.0)
    reader = _render(pages)
    assert len(reader.pages) == len(pages)
    for page in reader.pages:
        box = page.mediabox
        assert (float(box.width), float(box.height)) == pytest.approx(PAPER_PT[paper], abs=0.1)


def test_tab_and_edge_labels_printed(reference_skin: Skin) -> None:
    reader = _render(_pages(reference_skin, "A4", 5.0))
    text = "".join(page.extract_text() for page in reader.pages)
    for code in ("H", "B", "RA", "LA", "RL", "LL"):
        for letter in "ABCDEFG":
            assert text.count(f"{code}-{letter}") == 2


def test_render_is_byte_stable(reference_skin: Skin) -> None:
    document = NetDocument(pages=_pages(reference_skin, "A4", 5.0), lang="ru", grid_lines=True)
    renderer = PdfRenderer()
    assert renderer.render(document) == renderer.render(document)
