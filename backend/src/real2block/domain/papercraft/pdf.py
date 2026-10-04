"""PDF rendering with reportlab; the only module that imports it."""

import io
from collections.abc import Sequence
from itertools import pairwise
from pathlib import Path

from reportlab.lib.colors import Color
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from real2block.domain.color import Rgb
from real2block.domain.papercraft.document import PapercraftDocument
from real2block.domain.papercraft.instructions import (
    Cover,
    DiagramSpec,
    FigureView,
    Point2,
    Step,
    Tone,
)
from real2block.domain.papercraft.layout import (
    MARGIN_MM,
    RULER_MM,
    NetPage,
    PageFrame,
    Placement,
)
from real2block.domain.papercraft.legend import Legend
from real2block.domain.papercraft.net import PART_CODES, Label, NetPart, Point
from real2block.domain.papercraft.strings import Lang, part_name, text

TEXT_FONT = "Real2blockPixel"
TEXT_FONT_FILE = Path(__file__).parent / "fonts" / "PressStart2P-Regular.ttf"
LABEL_FONT = "Helvetica-Bold"

CUT_WIDTH_PT = 0.6
FOLD_WIDTH_PT = 0.4
FOLD_DASH = (3, 2)
GRID_WIDTH_PT = 0.1
GRID_ALPHA = 0.25
HATCH_STEP_MM = 1.5
HATCH_GRAY = 0.7
HEADING_SIZE_PT = 7.0
TITLE_SIZE_PT = 12.0
BODY_SIZE_PT = 6.0
LEADING = 1.6
LABEL_SIZE_PT = 5.0
RULER_TICK_MM = 10.0
RULER_TICK_H_MM = 2.0
RULER_GAP_MM = 2.0
TITLE_DROP_MM = 8.5
RULER_DROP_MM = 2.5

PAGE_TITLE_MM = 12.0
SECTION_GAP_MM = 6.0
VIEW_GAP_MM = 16.0
VIEW_HEIGHT_MM = 150.0
CAPTION_MM = 6.0
SAMPLE_MM = 30.0
SAMPLE_TAB_MM = 6.0
STEP_COLUMNS = 2
STEP_ROWS = 3
STEP_PAD_MM = 4.0
DIAGRAM_MAX_CELL_MM = 3.0
DIAGRAM_LINE_PT = 0.3
GLUE_LINE_PT = 1.2
NUMBERED_GRAY = 0.9
NUMBER_GRAY = 0.35
NUMBER_SIZE_RATIO = 0.45
LEGEND_ROW_MM = 6.0
LEGEND_SWATCH_MM = 4.5
LEGEND_COLUMNS_MM = (0.0, 14.0, 28.0, 60.0)

_BLACK = Color(0, 0, 0)
_WHITE = Color(1, 1, 1)
_NUMBERED_FILL = Color(NUMBERED_GRAY, NUMBERED_GRAY, NUMBERED_GRAY)
_NUMBER_INK = Color(NUMBER_GRAY, NUMBER_GRAY, NUMBER_GRAY)
_GLUE = Color(0.89, 0.34, 0.18)
_TONES: dict[Tone, Color] = {
    "top": Color(0.93, 0.93, 0.93),
    "front": Color(0.82, 0.82, 0.82),
    "side": Color(0.68, 0.68, 0.68),
}


def _fit_size(value: str, font: str, size: float, max_width_pt: float) -> float:
    width = pdfmetrics.stringWidth(value, font, size)
    return size if width <= max_width_pt else size * max_width_pt / width


def _color(rgb: Rgb) -> Color:
    return Color(rgb.r / 255, rgb.g / 255, rgb.b / 255)


def _wrap(value: str, font: str, size: float, width_pt: float) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in value.split():
        candidate = f"{current} {word}".strip()
        if current and pdfmetrics.stringWidth(candidate, font, size) > width_pt:
            lines.append(current)
            current = word
        else:
            current = candidate
    return [*lines, current] if current else lines


def _mm(value: float) -> str:
    return f"{round(value, 1):g}"


class _Page:
    """Maps page millimetres (y down) to PDF points (y up) and draws primitives."""

    def __init__(self, canvas: Canvas, frame: PageFrame) -> None:
        self.c = canvas
        self.frame = frame

    def xy(self, x_mm: float, y_mm: float) -> tuple[float, float]:
        return x_mm * mm, (self.frame.height - y_mm) * mm

    def line(self, a: Point, b: Point, dx: float, dy: float) -> None:
        self.c.line(*self.xy(a.x + dx, a.y + dy), *self.xy(b.x + dx, b.y + dy))

    def text(self, value: str, x: float, y: float, size: float = BODY_SIZE_PT) -> None:
        """Single line of localized text with its baseline at y."""
        # Helvetica has no Cyrillic, so localized text uses the vendored font.
        self.c.setFillColor(_BLACK)
        self.c.setFont(TEXT_FONT, size)
        self.c.drawString(*self.xy(x, y), value)

    def paragraph(self, value: str, x: float, y: float, width: float) -> float:
        """Wrapped text starting at baseline y; returns the y below the last line."""
        step = BODY_SIZE_PT * LEADING / mm
        for line in _wrap(value, TEXT_FONT, BODY_SIZE_PT, width * mm):
            self.text(line, x, y)
            y += step
        return y

    def title(self, value: str) -> float:
        """Page title at the top of the content area; returns the y below it."""
        frame = self.frame
        size = _fit_size(value, TEXT_FONT, TITLE_SIZE_PT, frame.content_w * mm)
        self.text(value, frame.content_x, MARGIN_MM + PAGE_TITLE_MM / 2, size)
        return MARGIN_MM + PAGE_TITLE_MM + SECTION_GAP_MM / 2

    def polygon(self, points: Sequence[tuple[float, float]], fill: Color | None) -> None:
        """Closed polygon in page millimetres, stroked with the current stroke state."""
        path = self.c.beginPath()
        first, *rest = points
        path.moveTo(*self.xy(*first))
        for p in rest:
            path.lineTo(*self.xy(*p))
        path.close()
        if fill is not None:
            self.c.setFillColor(fill)
        self.c.drawPath(path, stroke=1, fill=0 if fill is None else 1)

    def ruler(self, left: float, baseline: float, lang: Lang) -> None:
        """50 mm control line with 10 mm ticks and its label on the left."""
        c = self.c
        c.setStrokeColor(_BLACK)
        c.setLineWidth(CUT_WIDTH_PT)
        c.setDash()
        c.line(*self.xy(left, baseline), *self.xy(left + RULER_MM, baseline))
        for i in range(int(RULER_MM / RULER_TICK_MM) + 1):
            x = left + i * RULER_TICK_MM
            c.line(*self.xy(x, baseline), *self.xy(x, baseline - RULER_TICK_H_MM))
        c.setFont(TEXT_FONT, LABEL_SIZE_PT)
        c.drawRightString(*self.xy(left - RULER_GAP_MM, baseline), text(lang, "ruler"))

    def hatched(self, polygon: Sequence[Point], dx: float, dy: float) -> None:
        """White glue-tab polygon with gray hatching, clipped to its outline."""
        c = self.c
        c.saveState()
        path = c.beginPath()
        first, *rest = polygon
        path.moveTo(*self.xy(first.x + dx, first.y + dy))
        for p in rest:
            path.lineTo(*self.xy(p.x + dx, p.y + dy))
        path.close()
        c.setFillColor(_WHITE)
        c.clipPath(path, stroke=0, fill=1)
        xs = [p.x for p in polygon]
        ys = [p.y for p in polygon]
        span = (max(xs) - min(xs)) + (max(ys) - min(ys))
        c.setStrokeColor(Color(HATCH_GRAY, HATCH_GRAY, HATCH_GRAY))
        c.setLineWidth(GRID_WIDTH_PT)
        steps = int(span / HATCH_STEP_MM) + 1
        for i in range(steps):
            x = min(xs) + i * HATCH_STEP_MM
            self.line(Point(x, min(ys)), Point(x - span, min(ys) + span), dx, dy)
        c.restoreState()

    def tag(self, value: str, x: float, y: float, vertical: bool = False) -> None:
        """Latin label centered at (x, y) on a white background."""
        c = self.c
        c.saveState()
        c.translate(*self.xy(x, y))
        if vertical:
            c.rotate(90)
        width = pdfmetrics.stringWidth(value, LABEL_FONT, LABEL_SIZE_PT)
        c.setFillColor(_WHITE)
        c.rect(-width / 2 - 1, -LABEL_SIZE_PT / 2, width + 2, LABEL_SIZE_PT, stroke=0, fill=1)
        c.setFillColor(_BLACK)
        c.setFont(LABEL_FONT, LABEL_SIZE_PT)
        c.drawCentredString(0, -LABEL_SIZE_PT / 3, value)
        c.restoreState()


class _NetPainter:
    """Draws placed nets: cells, grid, tabs, cut and fold lines, labels."""

    def __init__(self, page: _Page, grid: bool, legend: Legend | None = None) -> None:
        self.page = page
        self.grid = grid
        # Numbered mode prints gray cells with color numbers instead of colors.
        self.numbers = legend if legend is not None and legend.mode == "numbered" else None

    def draw(self, placement: Placement) -> None:
        net, dx, dy = placement.net, placement.x, placement.y
        page, c = self.page, self.page.c
        for cell in net.cells:
            c.setFillColor(_color(cell.color) if self.numbers is None else _NUMBERED_FILL)
            x, y = page.xy(cell.x + dx, cell.y + dy + cell.size)
            c.rect(x, y, cell.size * mm, cell.size * mm, stroke=0, fill=1)
        if self.numbers is not None:
            self._numbers(net, self.numbers, dx, dy)
        if self.grid:
            self._grid(net, dx, dy)
        for tab in net.tabs:
            page.hatched(tab.polygon, dx, dy)
        self._lines(net, dx, dy)
        for label in [t.label for t in net.tabs] + list(net.edge_labels):
            self._label(label, dx, dy)

    def _numbers(self, net: NetPart, legend: Legend, dx: float, dy: float) -> None:
        page, c = self.page, self.page.c
        c.setFillColor(_NUMBER_INK)
        for cell in net.cells:
            number = legend.number_of(cell.color)
            if number is None:
                continue
            size = cell.size * mm * NUMBER_SIZE_RATIO
            c.setFont(LABEL_FONT, size)
            x, y = page.xy(cell.x + dx + cell.size / 2, cell.y + dy + cell.size / 2)
            c.drawCentredString(x, y - size / 3, str(number))

    def _grid(self, net: NetPart, dx: float, dy: float) -> None:
        page, c = self.page, self.page.c
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

    def _lines(self, net: NetPart, dx: float, dy: float) -> None:
        page, c = self.page, self.page.c
        c.setStrokeColor(_BLACK)
        c.setLineWidth(FOLD_WIDTH_PT)
        c.setDash(*FOLD_DASH)
        for a, b in net.fold:
            page.line(a, b, dx, dy)
        c.setDash()
        c.setLineWidth(CUT_WIDTH_PT)
        for a, b in net.cut:
            page.line(a, b, dx, dy)

    def _label(self, label: Label, dx: float, dy: float) -> None:
        self.page.tag(label.text, label.at.x + dx, label.at.y + dy, label.vertical)


class _GuidePainter:
    """Draws the cover, the printing guide and the assembly steps."""

    def __init__(self, page: _Page, lang: Lang) -> None:
        self.page = page
        self.lang = lang

    def t(self, key: str, **params: object) -> str:
        return text(self.lang, key, **params)

    def cover(self, cover: Cover) -> None:
        page, frame = self.page, self.page.frame
        y = page.title(self.t("cover.title"))
        half = (frame.content_w - VIEW_GAP_MM) / 2
        for i, view in enumerate((cover.front, cover.back)):
            x = frame.content_x + i * (half + VIEW_GAP_MM)
            self._view(view, x, y, half)
        y += VIEW_HEIGHT_MM + CAPTION_MM + SECTION_GAP_MM
        size = cover.size
        dims = {"width": _mm(size.width), "height": _mm(size.height), "depth": _mm(size.depth)}
        y = page.paragraph(self.t("cover.size", **dims), frame.content_x, y, frame.content_w)
        y = self._list(self.t("cover.parts"), self._part_lines(cover), y + SECTION_GAP_MM)
        tools = [self.t(key) for key in cover.tool_keys]
        self._list(self.t("cover.tools"), tools, y + SECTION_GAP_MM)

    def _part_lines(self, cover: Cover) -> list[str]:
        return [
            self.t("cover.part", name=part_name(self.lang, part), code=PART_CODES[part])
            for part in cover.parts
        ]

    def _list(self, heading: str, items: list[str], y: float) -> float:
        page, frame = self.page, self.page.frame
        page.text(heading, frame.content_x, y, HEADING_SIZE_PT)
        y += HEADING_SIZE_PT * LEADING / mm
        for item in items:
            y = page.paragraph(f"· {item}", frame.content_x, y, frame.content_w)
        return y

    def _view(self, view: FigureView, x: float, y: float, width: float) -> None:
        page, c = self.page, self.page.c
        cell = min(width / view.cols, VIEW_HEIGHT_MM / view.rows)
        left = x + (width - view.cols * cell) / 2
        for vc in view.cells:
            c.setFillColor(_color(vc.color))
            px, py = page.xy(left + vc.x * cell, y + (vc.y + 1) * cell)
            c.rect(px, py, cell * mm, cell * mm, stroke=0, fill=1)
        caption = self.t(f"cover.{view.side}")
        c.setFont(TEXT_FONT, HEADING_SIZE_PT)
        c.setFillColor(_BLACK)
        c.drawCentredString(*page.xy(x + width / 2, y + VIEW_HEIGHT_MM + CAPTION_MM), caption)

    def print_guide(self) -> None:
        page, frame = self.page, self.page.frame
        x, width = frame.content_x, frame.content_w
        y = page.title(self.t("print.title"))
        y = page.paragraph(self.t("print.scale"), x, y, width)
        y = page.paragraph(self.t("print.check"), x, y, width) + SECTION_GAP_MM
        label_w = pdfmetrics.stringWidth(self.t("ruler"), TEXT_FONT, LABEL_SIZE_PT) / mm
        page.ruler(x + label_w + RULER_GAP_MM, y, self.lang)
        y += SECTION_GAP_MM * 2
        page.text(self.t("print.legend"), x, y, HEADING_SIZE_PT)
        y = self._line_samples(y + SECTION_GAP_MM * 1.5)
        y = page.paragraph(self.t("print.labels"), x, y, width) + SECTION_GAP_MM
        page.text(self.t("print.score.title"), x, y, HEADING_SIZE_PT)
        y = page.paragraph(self.t("print.score"), x, y + SECTION_GAP_MM, width)
        page.paragraph(self.t("print.cut"), x, y, width)

    def _line_samples(self, y: float) -> float:
        page, c = self.page, self.page.c
        x = page.frame.content_x
        text_x = x + SAMPLE_MM + SECTION_GAP_MM
        c.setStrokeColor(_BLACK)
        c.setLineWidth(CUT_WIDTH_PT)
        c.setDash()
        page.line(Point(x, y), Point(x + SAMPLE_MM, y), 0, 0)
        page.text(self.t("line.cut"), text_x, y + 1)
        y += SECTION_GAP_MM
        c.setLineWidth(FOLD_WIDTH_PT)
        c.setDash(*FOLD_DASH)
        page.line(Point(x, y), Point(x + SAMPLE_MM, y), 0, 0)
        c.setDash()
        page.text(self.t("line.fold"), text_x, y + 1)
        y += SECTION_GAP_MM
        self._sample_tab(x, y + SAMPLE_TAB_MM / 2)
        page.text(self.t("line.tab"), text_x, y + 1)
        return y + SAMPLE_TAB_MM + SECTION_GAP_MM

    def _sample_tab(self, x: float, y: float) -> None:
        h = SAMPLE_TAB_MM
        a, b = Point(x, y), Point(x + SAMPLE_MM, y)
        polygon = (a, Point(x + h, y - h), Point(x + SAMPLE_MM - h, y - h), b)
        self.page.hatched(polygon, 0, 0)
        c = self.page.c
        c.setStrokeColor(_BLACK)
        c.setLineWidth(CUT_WIDTH_PT)
        for p, q in pairwise(polygon):
            self.page.line(p, q, 0, 0)
        c.setLineWidth(FOLD_WIDTH_PT)
        c.setDash(*FOLD_DASH)
        self.page.line(a, b, 0, 0)
        c.setDash()

    def steps(self, steps: tuple[Step, ...]) -> None:
        page, frame = self.page, self.page.frame
        top = page.title(self.t("steps.title"))
        cell_w = frame.content_w / STEP_COLUMNS
        cell_h = (frame.height - MARGIN_MM - top) / STEP_ROWS
        for i, step in enumerate(steps[: STEP_COLUMNS * STEP_ROWS]):
            col, row = i % STEP_COLUMNS, i // STEP_COLUMNS
            self._step(step, frame.content_x + col * cell_w, top + row * cell_h, cell_w, cell_h)

    def _step(self, step: Step, x: float, y: float, w: float, h: float) -> None:
        page = self.page
        inner = w - STEP_PAD_MM
        heading = self.t("step.label", index=step.index, title=self.t(step.title_key))
        page.text(heading, x, y, HEADING_SIZE_PT)
        body_y = page.paragraph(self.t(step.body_key), x, y + SECTION_GAP_MM, inner)
        self._diagram(step.diagram, x, body_y, inner, y + h - body_y - STEP_PAD_MM)

    def _diagram(self, spec: DiagramSpec, x: float, y: float, w: float, h: float) -> None:
        scale = min(w / spec.width, h / spec.height, DIAGRAM_MAX_CELL_MM)
        left = x + (w - spec.width * scale) / 2
        top = y + (h - spec.height * scale) / 2

        def at(p: Point2) -> tuple[float, float]:
            return left + p.x * scale, top + p.y * scale

        c = self.page.c
        c.setStrokeColor(_BLACK)
        c.setLineWidth(DIAGRAM_LINE_PT)
        c.setDash()
        for face in spec.faces:
            self.page.polygon([at(p) for p in face.points], _TONES[face.tone])
        c.setStrokeColor(_GLUE)
        c.setLineWidth(GLUE_LINE_PT)
        for zone in spec.glue_zones:
            self.page.polygon([at(p) for p in zone], None)
        for label in spec.labels:
            self.page.tag(label.text, *at(label.at))


class _LegendPainter:
    """Draws the color legend table."""

    def __init__(self, page: _Page, lang: Lang) -> None:
        self.page = page
        self.lang = lang

    def draw(self, legend: Legend) -> None:
        page, frame = self.page, self.page.frame
        y = page.title(text(self.lang, "legend.title"))
        hint = text(self.lang, f"legend.hint.{legend.mode}")
        y = page.paragraph(hint, frame.content_x, y, frame.content_w) + SECTION_GAP_MM
        keys = ("legend.number", "legend.color", "legend.hex", "legend.cells")
        self._row([text(self.lang, key) for key in keys], y, HEADING_SIZE_PT)
        for entry in legend.entries:
            y += LEGEND_ROW_MM
            self._swatch(entry.color, y)
            self._row([str(entry.number), "", entry.color.to_hex(), str(entry.cells)], y)
        if legend.other_cells:
            y += LEGEND_ROW_MM
            self._row(["", "", text(self.lang, "legend.other"), str(legend.other_cells)], y)

    def _row(self, values: list[str], y: float, size: float = BODY_SIZE_PT) -> None:
        x = self.page.frame.content_x
        for value, offset in zip(values, LEGEND_COLUMNS_MM, strict=True):
            if value:
                self.page.text(value, x + offset, y, size)

    def _swatch(self, color: Rgb, y: float) -> None:
        page, c = self.page, self.page.c
        x = page.frame.content_x + LEGEND_COLUMNS_MM[1]
        c.setStrokeColor(_BLACK)
        c.setLineWidth(GRID_WIDTH_PT)
        c.setFillColor(_color(color))
        px, py = page.xy(x, y + (LEGEND_SWATCH_MM - LEGEND_ROW_MM) / 2 + 1)
        c.rect(px, py, LEGEND_SWATCH_MM * mm, LEGEND_SWATCH_MM * mm, stroke=1, fill=1)


class PdfRenderer:
    """Renders a `PapercraftDocument` into vector PDF bytes."""

    def __init__(self) -> None:
        if TEXT_FONT not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(TEXT_FONT, str(TEXT_FONT_FILE)))

    def render(self, document: PapercraftDocument) -> bytes:
        """Cover, printing guide, nets, assembly, legend; byte-stable for equal input."""
        buf = io.BytesIO()
        frame = document.frame
        canvas = Canvas(buf, pagesize=(frame.width * mm, frame.height * mm), invariant=1)
        canvas.setTitle(text(document.lang, "doc.title"))
        guide = _GuidePainter(_Page(canvas, frame), document.lang)
        guide.cover(document.cover)
        canvas.showPage()
        guide.print_guide()
        canvas.showPage()
        for net_page in document.pages:
            self._net_page(_Page(canvas, net_page.frame), net_page, document)
            canvas.showPage()
        guide.steps(document.steps)
        canvas.showPage()
        _LegendPainter(_Page(canvas, frame), document.lang).draw(document.legend)
        canvas.showPage()
        canvas.save()
        return buf.getvalue()

    def _net_page(self, page: _Page, net_page: NetPage, doc: PapercraftDocument) -> None:
        parts = ", ".join(part_name(doc.lang, p.net.part) for p in net_page.placements)
        number = page.c.getPageNumber()
        self._header(page, text(doc.lang, "page.net", parts=parts, page=number), doc.lang)
        painter = _NetPainter(page, doc.grid_lines, doc.legend)
        for placement in net_page.placements:
            painter.draw(placement)

    def _header(self, page: _Page, title: str, lang: Lang) -> None:
        frame = page.frame
        size = _fit_size(title, TEXT_FONT, HEADING_SIZE_PT, frame.content_w * mm)
        page.text(title, frame.content_x, frame.content_y - TITLE_DROP_MM, size)
        # The ruler sits on its own line so a long title can never cover it.
        left = frame.content_x + frame.content_w - RULER_MM
        page.ruler(left, frame.content_y - RULER_DROP_MM, lang)
