"""Net pages from tech.md §4.2-4.3 and §10.10: line styles, ruler, grid, page sizes."""

import io
from collections import Counter
from dataclasses import replace

import pytest
from pypdf import PdfReader
from pypdf.generic import ContentStream

from real2block.domain.papercraft.document import PapercraftDocument
from real2block.domain.papercraft.instructions import build_cover, build_steps
from real2block.domain.papercraft.layout import NetPage, Paper, layout_pages
from real2block.domain.papercraft.legend import PrintMode, prepare_skin
from real2block.domain.papercraft.net import Segment, build_net_part
from real2block.domain.papercraft.pdf import PdfRenderer
from real2block.domain.papercraft.strings import Lang
from real2block.domain.skin.geometry import PART_IDS
from real2block.domain.skin.skin import Skin
from tests.helpers import PdfSegment, StrokeStyle, pdf_segments

PT_PER_MM = 72 / 25.4
PAPER_PT: dict[Paper, tuple[float, float]] = {"A4": (595.28, 841.89), "Letter": (612.0, 792.0)}
CUT = (0.6, ())
FOLD = (0.4, (3.0, 2.0))
GRID_WIDTH = 0.1
RULER_TICKS = 6
NET_OFFSET = 2  # cover and printing guide come first


def _pages(skin: Skin, paper: Paper, pixel_mm: float) -> tuple[NetPage, ...]:
    nets = [build_net_part(skin, part, "classic", pixel_mm) for part in PART_IDS]
    return layout_pages(nets, paper)


def _document(
    skin: Skin,
    pages: tuple[NetPage, ...],
    grid: bool = True,
    lang: Lang = "en",
    mode: PrintMode = "color",
) -> PapercraftDocument:
    return PapercraftDocument(
        frame=pages[0].frame,
        cover=build_cover(skin, "classic", 5.0),
        pages=pages,
        steps=build_steps("classic"),
        legend=prepare_skin(skin, "classic", mode).legend,
        lang=lang,
        grid_lines=grid,
    )


def _render(skin: Skin, pages: tuple[NetPage, ...], grid: bool = True) -> PdfReader:
    return PdfReader(io.BytesIO(PdfRenderer().render(_document(skin, pages, grid))))


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
    reader = _render(reference_skin, pages)
    for index, page in enumerate(pages):
        drawn = pdf_segments(reader, NET_OFFSET + index)
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
    reader = _render(reference_skin, pages, grid=grid)
    for index, page in enumerate(pages):
        drawn = pdf_segments(reader, NET_OFFSET + index)
        lines = [
            seg
            for (style, seg), n in drawn.items()
            for _ in range(n)
            if style.width == GRID_WIDTH and style.alpha_state is not None
        ]
        faces = [f for pl in page.placements for f in pl.net.faces]
        expected = sum(f.cols - 1 + f.rows - 1 for f in faces) if grid else 0
        assert len(lines) == expected
        alpha = reader.pages[NET_OFFSET + index]["/Resources"].get("/ExtGState", {})
        assert any(float(state.get("/CA", 1)) == 0.25 for state in alpha.values()) == grid


@pytest.mark.parametrize("paper", ["A4", "Letter"])
def test_page_size_and_count(reference_skin: Skin, paper: Paper) -> None:
    pages = _pages(reference_skin, paper, 5.0)
    reader = _render(reference_skin, pages)
    # Assembly and legend follow the nets.
    assert len(reader.pages) == NET_OFFSET + len(pages) + 2
    for page in reader.pages:
        box = page.mediabox
        assert (float(box.width), float(box.height)) == pytest.approx(PAPER_PT[paper], abs=0.1)


def test_tab_and_edge_labels_printed(reference_skin: Skin) -> None:
    pages = _pages(reference_skin, "A4", 5.0)
    reader = _render(reference_skin, pages)
    nets = reader.pages[NET_OFFSET : NET_OFFSET + len(pages)]
    text = "".join(page.extract_text() for page in nets)
    for code in ("H", "B", "RA", "LA", "RL", "LL"):
        for letter in "ABCDEFG":
            assert text.count(f"{code}-{letter}") == 2


def test_render_is_byte_stable(reference_skin: Skin) -> None:
    document = _document(reference_skin, _pages(reference_skin, "A4", 5.0), lang="ru")
    renderer = PdfRenderer()
    assert renderer.render(document) == renderer.render(document)


def test_page_order_cover_guide_nets_assembly(reference_skin: Skin) -> None:
    pages = _pages(reference_skin, "A4", 5.0)
    document = _document(reference_skin, pages, lang="ru")
    reader = PdfReader(io.BytesIO(PdfRenderer().render(document)))
    texts = [page.extract_text() for page in reader.pages]
    assert "Бумажная фигурка" in texts[0]
    assert "80 \N{MULTIPLICATION SIGN} 160 \N{MULTIPLICATION SIGN} 40 мм" in texts[0]
    assert "Как печатать и резать" in texts[1]
    assert "50 мм" in texts[1]
    assert all("Развёртка" in t for t in texts[NET_OFFSET : NET_OFFSET + len(pages)])
    assert "стр. 3" in texts[NET_OFFSET]
    assert [f"Шаг {i}." in texts[-2] for i in range(1, 7)] == [True] * 6
    assert "Легенда цветов" in texts[-1]


def test_guide_page_has_line_legend_and_ruler(reference_skin: Skin) -> None:
    reader = _render(reference_skin, _pages(reference_skin, "A4", 5.0))
    drawn = pdf_segments(reader, 1)
    cuts = _drawn(drawn, *CUT)
    folds = _drawn(drawn, *FOLD)
    lengths = sorted(round(abs(b[0] - a[0]) + abs(b[1] - a[1]), 1) for a, b in cuts.elements())
    assert lengths[-1] == pytest.approx(50 * PT_PER_MM, abs=0.05)
    assert len(folds) >= 2  # a fold sample and the fold edge of the tab sample


def _fills(reader: PdfReader, index: int) -> set[tuple[float, ...]]:
    ops = ContentStream(reader.pages[index].get_contents(), reader).operations
    return {tuple(round(float(v), 3) for v in operands) for operands, op in ops if op == b"rg"}


def test_numbered_mode_prints_gray_cells_with_numbers(reference_skin: Skin) -> None:
    prepared = prepare_skin(reference_skin, "classic", "numbered")
    nets = [build_net_part(prepared.skin, p, "classic", 5.0) for p in PART_IDS]
    pages = layout_pages(nets, "A4")
    document = replace(_document(prepared.skin, pages, mode="numbered"), legend=prepared.legend)
    reader = PdfReader(io.BytesIO(PdfRenderer().render(document)))
    for index in range(NET_OFFSET, NET_OFFSET + len(pages)):
        # Light gray cells, gray numbers, white label boxes, black text.
        assert _fills(reader, index) <= {(0.9, 0.9, 0.9), (0.35, 0.35, 0.35), (1, 1, 1), (0, 0, 0)}
    words = reader.pages[NET_OFFSET].extract_text().split()
    assert {str(e.number) for e in prepared.legend.entries[:5]} <= set(words)


@pytest.mark.parametrize("mode", ["color", "numbered"])
def test_legend_page_lists_every_color(reference_skin: Skin, mode: PrintMode) -> None:
    prepared = prepare_skin(reference_skin, "classic", mode)
    pages = _pages(prepared.skin, "A4", 5.0)
    document = replace(_document(prepared.skin, pages), legend=prepared.legend)
    reader = PdfReader(io.BytesIO(PdfRenderer().render(document)))
    legend_text = reader.pages[-1].extract_text()
    for entry in prepared.legend.entries:
        assert entry.color.to_hex() in legend_text
        assert str(entry.cells) in legend_text
    if prepared.legend.other_cells:
        assert "other" in legend_text
