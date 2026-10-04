"""PDF rendering with reportlab; the only module that imports it."""

import io
from pathlib import Path

from reportlab.lib.colors import Color
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from blockfold.domain.color import Rgb
from blockfold.domain.papercraft.document import NetDocument
from blockfold.domain.papercraft.layout import RULER_MM, NetPage, PageFrame, Placement
from blockfold.domain.papercraft.net import Label, NetPart, NetTab, Point
from blockfold.domain.papercraft.strings import Lang, part_name, text

HEADING_FONT = "BlockfoldPixel"
HEADING_FONT_FILE = Path(__file__).parent / "fonts" / "PressStart2P-Regular.ttf"
LABEL_FONT = "Helvetica-Bold"

CUT_WIDTH_PT = 0.6
FOLD_WIDTH_PT = 0.4
FOLD_DASH = (3, 2)
GRID_WIDTH_PT = 0.1
GRID_ALPHA = 0.25
HATCH_STEP_MM = 1.5
HATCH_GRAY = 0.7
HEADING_SIZE_PT = 7.0
LABEL_SIZE_PT = 5.0
RULER_TICK_MM = 10.0

_BLACK = Color(0, 0, 0)
_WHITE = Color(1, 1, 1)


def _color(rgb: Rgb) -> Color:
    return Color(rgb.r / 255, rgb.g / 255, rgb.b / 255)


class _Page:
    """Maps page millimetres (y down) to PDF points (y up)."""

    def __init__(self, canvas: Canvas, frame: PageFrame) -> None:
        self.c = canvas
        self.frame = frame

    def xy(self, x_mm: float, y_mm: float) -> tuple[float, float]:
        return x_mm * mm, (self.frame.height - y_mm) * mm

    def line(self, a: Point, b: Point, dx: float, dy: float) -> None:
        self.c.line(*self.xy(a.x + dx, a.y + dy), *self.xy(b.x + dx, b.y + dy))


class PdfRenderer:
    """Renders a `NetDocument` into vector PDF bytes."""

    def __init__(self) -> None:
        if HEADING_FONT not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(HEADING_FONT, str(HEADING_FONT_FILE)))

    def render(self, document: NetDocument) -> bytes:
        """Draw every page; output is byte-stable for equal input."""
        buf = io.BytesIO()
        first = document.pages[0].frame
        canvas = Canvas(buf, pagesize=(first.width * mm, first.height * mm), invariant=1)
        canvas.setTitle(text(document.lang, "doc.title"))
        for number, page in enumerate(document.pages, start=1):
            canvas.setPageSize((page.frame.width * mm, page.frame.height * mm))
            self._net_page(_Page(canvas, page.frame), page, number, document)
            canvas.showPage()
        canvas.save()
        return buf.getvalue()

    def _net_page(self, page: _Page, net_page: NetPage, number: int, doc: NetDocument) -> None:
        parts = ", ".join(part_name(doc.lang, p.net.part) for p in net_page.placements)
        self._header(page, text(doc.lang, "page.net", parts=parts, page=number), doc.lang)
        for placement in net_page.placements:
            self._net(page, placement, doc.grid_lines)

    def _header(self, page: _Page, title: str, lang: Lang) -> None:
        c, frame = page.c, page.frame
        baseline = frame.content_y - frame.content_y / 4
        c.setFillColor(_BLACK)
        c.setFont(HEADING_FONT, HEADING_SIZE_PT)
        c.drawString(*page.xy(frame.content_x, baseline), title)
        right = frame.content_x + frame.content_w
        left = right - RULER_MM
        c.setStrokeColor(_BLACK)
        c.setLineWidth(CUT_WIDTH_PT)
        c.setDash()
        c.line(*page.xy(left, baseline), *page.xy(right, baseline))
        ticks = int(RULER_MM / RULER_TICK_MM)
        for i in range(ticks + 1):
            x = left + i * RULER_TICK_MM
            c.line(*page.xy(x, baseline), *page.xy(x, baseline - 2))
        # Helvetica has no Cyrillic, so localized text uses the vendored font.
        c.setFont(HEADING_FONT, LABEL_SIZE_PT)
        c.drawCentredString(*page.xy(left + RULER_MM / 2, baseline + 3.5), text(lang, "ruler"))

    def _net(self, page: _Page, placement: Placement, grid: bool) -> None:
        net, dx, dy = placement.net, placement.x, placement.y
        c = page.c
        for cell in net.cells:
            c.setFillColor(_color(cell.color))
            x, y = page.xy(cell.x + dx, cell.y + dy + cell.size)
            c.rect(x, y, cell.size * mm, cell.size * mm, stroke=0, fill=1)
        if grid:
            self._grid(page, net, dx, dy)
        for tab in net.tabs:
            self._tab(page, tab, dx, dy)
        self._lines(page, net, dx, dy)
        for label in [t.label for t in net.tabs] + list(net.edge_labels):
            self._label(page, label, dx, dy)

    def _grid(self, page: _Page, net: NetPart, dx: float, dy: float) -> None:
        c = page.c
        c.saveState()
        c.setStrokeColor(_BLACK, alpha=GRID_ALPHA)
        c.setLineWidth(GRID_WIDTH_PT)
        for f in net.faces:
            right, bottom = f.x + f.cols * f.cell, f.y + f.rows * f.cell
            for i in range(1, f.cols):
                x = f.x + i * f.cell
                page.line(Point(x, f.y), Point(x, bottom), dx, dy)
            for j in range(1, f.rows):
                y = f.y + j * f.cell
                page.line(Point(f.x, y), Point(right, y), dx, dy)
        c.restoreState()

    def _tab(self, page: _Page, tab: NetTab, dx: float, dy: float) -> None:
        c = page.c
        c.saveState()
        path = c.beginPath()
        first, *rest = tab.polygon
        path.moveTo(*page.xy(first.x + dx, first.y + dy))
        for p in rest:
            path.lineTo(*page.xy(p.x + dx, p.y + dy))
        path.close()
        c.setFillColor(_WHITE)
        c.clipPath(path, stroke=0, fill=1)
        xs = [p.x for p in tab.polygon]
        ys = [p.y for p in tab.polygon]
        span = (max(xs) - min(xs)) + (max(ys) - min(ys))
        c.setStrokeColor(Color(HATCH_GRAY, HATCH_GRAY, HATCH_GRAY))
        c.setLineWidth(GRID_WIDTH_PT)
        steps = int(span / HATCH_STEP_MM) + 1
        for i in range(steps):
            x = min(xs) + i * HATCH_STEP_MM
            page.line(Point(x, min(ys)), Point(x - span, min(ys) + span), dx, dy)
        c.restoreState()

    def _lines(self, page: _Page, net: NetPart, dx: float, dy: float) -> None:
        c = page.c
        c.setStrokeColor(_BLACK)
        c.setLineWidth(FOLD_WIDTH_PT)
        c.setDash(*FOLD_DASH)
        for a, b in net.fold:
            page.line(a, b, dx, dy)
        c.setDash()
        c.setLineWidth(CUT_WIDTH_PT)
        for a, b in net.cut:
            page.line(a, b, dx, dy)

    def _label(self, page: _Page, label: Label, dx: float, dy: float) -> None:
        c = page.c
        c.saveState()
        c.translate(*page.xy(label.at.x + dx, label.at.y + dy))
        if label.vertical:
            c.rotate(90)
        width = pdfmetrics.stringWidth(label.text, LABEL_FONT, LABEL_SIZE_PT)
        c.setFillColor(_WHITE)
        c.rect(-width / 2 - 1, -LABEL_SIZE_PT / 2, width + 2, LABEL_SIZE_PT, stroke=0, fill=1)
        c.setFillColor(_BLACK)
        c.setFont(LABEL_FONT, LABEL_SIZE_PT)
        c.drawCentredString(0, -LABEL_SIZE_PT / 3, label.text)
        c.restoreState()
