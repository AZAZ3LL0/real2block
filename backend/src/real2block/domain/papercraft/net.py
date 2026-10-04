"""Box nets (tech.md §4.2): face placement, cut/fold lines and glue tabs in millimetres."""

import io
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

import numpy as np
from PIL import Image

from real2block.domain.color import Rgb
from real2block.domain.skin.geometry import (
    PARTS,
    BoxSpec,
    FaceId,
    Model,
    PartId,
    Rect,
    part_box,
    uv_rect,
)
from real2block.domain.skin.skin import Skin

Side = Literal["N", "S", "W", "E"]

TAB_HEIGHT_MM = 6.0
EDGE_LABEL_INSET_MM = 2.0

PART_CODES: Mapping[PartId, str] = MappingProxyType(
    {
        "head": "H",
        "body": "B",
        "right_arm": "RA",
        "left_arm": "LA",
        "right_leg": "RL",
        "left_leg": "LL",
    }
)

_NORMALS: Mapping[Side, tuple[int, int]] = MappingProxyType(
    {"N": (0, -1), "S": (0, 1), "W": (-1, 0), "E": (1, 0)}
)


@dataclass(frozen=True, slots=True)
class TabSpec:
    """Glue tab on a face edge and the edge it is glued to."""

    letter: str
    face: FaceId
    side: Side
    mate_face: FaceId
    mate_side: Side


# Order defines letters A..G: three free edges of top, of bottom, then the back seam.
TABS: tuple[TabSpec, ...] = (
    TabSpec("A", "top", "W", "right", "N"),
    TabSpec("B", "top", "E", "left", "N"),
    TabSpec("C", "top", "N", "back", "N"),
    TabSpec("D", "bottom", "W", "right", "S"),
    TabSpec("E", "bottom", "E", "left", "S"),
    TabSpec("F", "bottom", "S", "back", "S"),
    TabSpec("G", "back", "E", "right", "W"),
)

# Edges where two faces meet in the cross; each pair is folded once.
SHARED_EDGES: tuple[tuple[FaceId, Side], ...] = (
    ("top", "S"),
    ("bottom", "N"),
    ("right", "E"),
    ("left", "W"),
    ("left", "E"),
)


@dataclass(frozen=True, slots=True)
class FacePlacement:
    """Where a face sits in the net, in cells, and whether it is drawn flipped."""

    face: FaceId
    rect: Rect
    flip_vertical: bool


def net_faces(box: BoxSpec) -> tuple[FacePlacement, ...]:
    """Cross layout: side strip right-front-left-back, top and bottom on front."""
    w, h, d = box.w, box.h, box.d
    return (
        FacePlacement("top", Rect(d, 0, w, d), flip_vertical=False),
        FacePlacement("right", Rect(0, d, d, h), flip_vertical=False),
        FacePlacement("front", Rect(d, d, w, h), flip_vertical=False),
        FacePlacement("left", Rect(d + w, d, d, h), flip_vertical=False),
        FacePlacement("back", Rect(2 * d + w, d, w, h), flip_vertical=False),
        FacePlacement("bottom", Rect(d, d + h, w, d), flip_vertical=True),
    )


def net_size(box: BoxSpec) -> tuple[int, int]:
    """Net bounding box in cells, without tabs."""
    return 2 * box.d + 2 * box.w, 2 * box.d + box.h


def source_pixel(placement: FacePlacement, texture: Rect, i: int, j: int) -> tuple[int, int]:
    """Texture pixel shown in local cell (i, j) of a placed face."""
    row = texture.h - 1 - j if placement.flip_vertical else j
    return texture.x + i, texture.y + row


def box_cell_map(box: BoxSpec, origin: tuple[int, int]) -> dict[tuple[int, int], tuple[int, int]]:
    """Map of net cell (x, y) to texture pixel (x, y) for a box at a UV origin."""
    mapping: dict[tuple[int, int], tuple[int, int]] = {}
    for placement in net_faces(box):
        texture = uv_rect(box, origin, placement.face)
        rect = placement.rect
        for j in range(rect.h):
            for i in range(rect.w):
                mapping[(rect.x + i, rect.y + j)] = source_pixel(placement, texture, i, j)
    return mapping


def net_cell_map(part: PartId, model: Model) -> dict[tuple[int, int], tuple[int, int]]:
    """Map of net cell (x, y) to base-layer texture pixel (x, y) for a part."""
    spec = PARTS[model][part]
    return box_cell_map(spec.box, spec.base)


def render_debug_png(skin: Skin, part: PartId, model: Model) -> bytes:
    """Raster net, one cell per pixel, transparent outside faces; used by golden tests."""
    width, height = net_size(part_box(part, model))
    out = np.zeros((height, width, 4), dtype=np.uint8)
    for (x, y), (u, v) in net_cell_map(part, model).items():
        out[y, x] = skin.pixels[v, u]
    buf = io.BytesIO()
    Image.fromarray(out).save(buf, format="PNG")
    return buf.getvalue()


@dataclass(frozen=True, slots=True)
class Point:
    """Point in millimetres, y pointing down."""

    x: float
    y: float


Segment = tuple[Point, Point]


@dataclass(frozen=True, slots=True)
class NetCell:
    """One printed pixel cell."""

    x: float
    y: float
    size: float
    color: Rgb


@dataclass(frozen=True, slots=True)
class NetFace:
    """Face rectangle in millimetres with its cell grid size."""

    face: FaceId
    x: float
    y: float
    cols: int
    rows: int
    cell: float


@dataclass(frozen=True, slots=True)
class Label:
    """Tab label text anchored at its center; vertical labels run along the edge."""

    text: str
    at: Point
    vertical: bool


@dataclass(frozen=True, slots=True)
class NetTab:
    """Trapezoid glue tab: polygon P0, P0', P1', P1 with P0-P1 on the face edge."""

    polygon: tuple[Point, Point, Point, Point]
    label: Label


@dataclass(frozen=True, slots=True)
class NetPart:
    """Printable net of one part; coordinates relative to its bounding box."""

    part: PartId
    code: str
    width: float
    height: float
    cells: tuple[NetCell, ...]
    faces: tuple[NetFace, ...]
    cut: tuple[Segment, ...]
    fold: tuple[Segment, ...]
    tabs: tuple[NetTab, ...]
    edge_labels: tuple[Label, ...]


class _Frame:
    """Converts net cell coordinates to millimetres within the part bounding box."""

    def __init__(self, box: BoxSpec, pixel_mm: float) -> None:
        self.cell = pixel_mm
        self.rects = {p.face: p.rect for p in net_faces(box)}

    def point(self, cx: float, cy: float) -> Point:
        return Point(cx * self.cell, TAB_HEIGHT_MM + cy * self.cell)

    def edge(self, face: FaceId, side: Side) -> Segment:
        r = self.rects[face]
        corners = {
            "N": ((r.x, r.y), (r.x + r.w, r.y)),
            "S": ((r.x, r.y + r.h), (r.x + r.w, r.y + r.h)),
            "W": ((r.x, r.y), (r.x, r.y + r.h)),
            "E": ((r.x + r.w, r.y), (r.x + r.w, r.y + r.h)),
        }
        (x0, y0), (x1, y1) = corners[side]
        return self.point(x0, y0), self.point(x1, y1)


def _offset(p: Point, dx: float, dy: float) -> Point:
    return Point(p.x + dx, p.y + dy)


def _tab(frame: _Frame, spec: TabSpec, text: str) -> tuple[NetTab, tuple[Segment, ...]]:
    p0, p1 = frame.edge(spec.face, spec.side)
    nx, ny = _NORMALS[spec.side]
    tx, ty = (1, 0) if spec.side in ("N", "S") else (0, 1)
    hgt = TAB_HEIGHT_MM
    q0 = _offset(p0, nx * hgt + tx * hgt, ny * hgt + ty * hgt)
    q1 = _offset(p1, nx * hgt - tx * hgt, ny * hgt - ty * hgt)
    mid = Point((p0.x + p1.x) / 2 + nx * hgt / 2, (p0.y + p1.y) / 2 + ny * hgt / 2)
    tab = NetTab((p0, q0, q1, p1), Label(text, mid, vertical=spec.side in ("W", "E")))
    return tab, ((p0, q0), (q0, q1), (q1, p1))


def _edge_label(frame: _Frame, face: FaceId, side: Side, text: str) -> Label:
    p0, p1 = frame.edge(face, side)
    nx, ny = _NORMALS[side]
    inset = EDGE_LABEL_INSET_MM
    at = Point((p0.x + p1.x) / 2 - nx * inset, (p0.y + p1.y) / 2 - ny * inset)
    return Label(text, at, vertical=side in ("W", "E"))


def _cells(skin: Skin, part: PartId, model: Model, frame: _Frame) -> tuple[NetCell, ...]:
    return tuple(
        NetCell(*_xy(frame.point(x, y)), frame.cell, skin.rgb_at(u, v))
        for (x, y), (u, v) in sorted(net_cell_map(part, model).items())
    )


def _xy(p: Point) -> tuple[float, float]:
    return p.x, p.y


def build_net_part(skin: Skin, part: PartId, model: Model, pixel_mm: float) -> NetPart:
    """Net of one part from an already flattened skin."""
    box = part_box(part, model)
    frame = _Frame(box, pixel_mm)
    code = PART_CODES[part]
    tabs: list[NetTab] = []
    cut: list[Segment] = []
    labels: list[Label] = []
    for spec in TABS:
        text = f"{code}-{spec.letter}"
        tab, sides = _tab(frame, spec, text)
        tabs.append(tab)
        cut.extend(sides)
        cut.append(frame.edge(spec.mate_face, spec.mate_side))
        labels.append(_edge_label(frame, spec.mate_face, spec.mate_side, text))
    fold = [frame.edge(face, side) for face, side in SHARED_EDGES]
    fold.extend(frame.edge(spec.face, spec.side) for spec in TABS)
    faces = tuple(
        NetFace(p.face, *_xy(frame.point(p.rect.x, p.rect.y)), p.rect.w, p.rect.h, pixel_mm)
        for p in net_faces(box)
    )
    cols, rows = net_size(box)
    return NetPart(
        part=part,
        code=code,
        width=cols * pixel_mm + TAB_HEIGHT_MM,
        height=rows * pixel_mm + 2 * TAB_HEIGHT_MM,
        cells=_cells(skin, part, model, frame),
        faces=faces,
        cut=tuple(cut),
        fold=tuple(fold),
        tabs=tuple(tabs),
        edge_labels=tuple(labels),
    )
