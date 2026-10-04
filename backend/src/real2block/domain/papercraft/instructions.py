"""Cover and assembly instruction model (tech.md §5.5): data only, no drawing."""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from real2block.domain.color import Rgb
from real2block.domain.papercraft.net import PART_CODES, TABS, Side
from real2block.domain.skin.geometry import PART_IDS, BoxSpec, FaceId, Model, PartId, part_box
from real2block.domain.skin.skin import Skin

ViewSide = Literal["front", "back"]
Tone = Literal["top", "front", "side"]

Vec3 = tuple[float, float, float]

EXPLODE_CELLS = 6.0
"""Distance parts are pulled apart in the assembly diagram, in skin pixels."""

_COS30 = math.cos(math.radians(30))
_SIN30 = 0.5

# The isometric view looks from the front, from the figure's right side and from above.
VISIBLE_FACES: tuple[FaceId, ...] = ("top", "front", "right")
_TONES: Mapping[FaceId, Tone] = MappingProxyType({"top": "top", "front": "front", "right": "side"})

TOOL_KEYS: tuple[str, ...] = ("tool.scissors", "tool.glue", "tool.ruler", "tool.scoring")


@dataclass(frozen=True, slots=True)
class ViewCell:
    """One pixel of an orthographic figure view, in cells from the top-left."""

    x: int
    y: int
    color: Rgb


@dataclass(frozen=True, slots=True)
class FigureView:
    """Orthographic front or back view of the assembled figure."""

    side: ViewSide
    cols: int
    rows: int
    cells: tuple[ViewCell, ...]


@dataclass(frozen=True, slots=True)
class FigureSize:
    """Assembled figure size in millimetres."""

    width: float
    height: float
    depth: float


@dataclass(frozen=True, slots=True)
class Cover:
    """Cover page content."""

    front: FigureView
    back: FigureView
    size: FigureSize
    parts: tuple[PartId, ...]
    tool_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Point2:
    """Diagram point; y points down."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class DiagramPolygon:
    """Filled face of a box in the diagram."""

    points: tuple[Point2, ...]
    tone: Tone


@dataclass(frozen=True, slots=True)
class DiagramLabel:
    """Text placed at a diagram point."""

    text: str
    at: Point2


@dataclass(frozen=True, slots=True)
class DiagramSpec:
    """Isometric sketch: faces back to front, glue zone frames and labels."""

    width: float
    height: float
    faces: tuple[DiagramPolygon, ...]
    glue_zones: tuple[tuple[Point2, ...], ...]
    labels: tuple[DiagramLabel, ...]


@dataclass(frozen=True, slots=True)
class Step:
    """One assembly step; texts are keys into `strings.py`."""

    index: int
    title_key: str
    body_key: str
    diagram: DiagramSpec


@dataclass(frozen=True, slots=True)
class PlacedBox:
    """Box of a part at a position in figure space (cells; x from the figure's right, y down,
    z from front to back)."""

    part: PartId
    box: BoxSpec
    origin: Vec3


# Orthographic views


@dataclass(frozen=True, slots=True)
class _Slot:
    part: PartId
    x: int
    y: int


def _view_slots(model: Model, side: ViewSide) -> tuple[_Slot, ...]:
    head, body = part_box("head", model), part_box("body", model)
    arm, leg = part_box("right_arm", model), part_box("right_leg", model)
    body_x, legs_y = arm.w, head.h + body.h
    # Seen from behind, the figure's left side is on the viewer's left.
    arms, legs = _NEAR_FAR[side]
    return (
        _Slot("head", body_x + (body.w - head.w) // 2, 0),
        _Slot("body", body_x, head.h),
        _Slot(arms[0], 0, head.h),
        _Slot(arms[1], body_x + body.w, head.h),
        _Slot(legs[0], body_x, legs_y),
        _Slot(legs[1], body_x + leg.w, legs_y),
    )


_NEAR_FAR: Mapping[ViewSide, tuple[tuple[PartId, PartId], tuple[PartId, PartId]]] = (
    MappingProxyType(
        {
            "front": (("right_arm", "left_arm"), ("right_leg", "left_leg")),
            "back": (("left_arm", "right_arm"), ("left_leg", "right_leg")),
        }
    )
)
"""Limbs on the viewer's left and right for each view."""


def figure_size_cells(model: Model) -> tuple[int, int, int]:
    """Assembled figure width, height and depth in skin pixels."""
    head, body = part_box("head", model), part_box("body", model)
    arm, leg = part_box("right_arm", model), part_box("right_leg", model)
    return body.w + 2 * arm.w, head.h + body.h + leg.h, max(head.d, body.d)


def figure_view(skin: Skin, model: Model, side: ViewSide) -> FigureView:
    """Front or back of every part, arranged as the assembled figure."""
    cells: list[ViewCell] = []
    for slot in _view_slots(model, side):
        pixels = skin.face(slot.part, side, model=model)
        rows, cols = pixels.shape[:2]
        for j in range(rows):
            for i in range(cols):
                r, g, b = (int(c) for c in pixels[j, i, :3])
                cells.append(ViewCell(slot.x + i, slot.y + j, Rgb(r, g, b)))
    cols, rows, _ = figure_size_cells(model)
    return FigureView(side, cols, rows, tuple(cells))


def build_cover(skin: Skin, model: Model, pixel_mm: float) -> Cover:
    """Cover with both views, finished size and the parts list."""
    width, height, depth = figure_size_cells(model)
    return Cover(
        front=figure_view(skin, model, "front"),
        back=figure_view(skin, model, "back"),
        size=FigureSize(width * pixel_mm, height * pixel_mm, depth * pixel_mm),
        parts=PART_IDS,
        tool_keys=TOOL_KEYS,
    )


# Isometric diagrams


def _project(p: Vec3) -> Point2:
    x, y, z = p
    return Point2((x - z) * _COS30, y - (x + z) * _SIN30)


def _face_corners(placed: PlacedBox, face: FaceId) -> tuple[Vec3, Vec3, Vec3, Vec3]:
    """Corners of a visible face in figure space, clockwise from the top-left."""
    x, y, z = placed.origin
    w, h, d = placed.box.w, placed.box.h, placed.box.d
    if face == "top":
        return (x, y, z + d), (x + w, y, z + d), (x + w, y, z), (x, y, z)
    if face == "front":
        return (x, y, z), (x + w, y, z), (x + w, y + h, z), (x, y + h, z)
    return (x, y, z + d), (x, y, z), (x, y + h, z), (x, y + h, z + d)


def _net_to_box(box: BoxSpec, face: FaceId, u: float, v: float) -> Vec3:
    """Box-local point of a net face at fractions (u, v) of its width and height."""
    w, h, d = box.w, box.h, box.d
    folded: Mapping[FaceId, Vec3] = {
        "front": (u * w, v * h, 0.0),
        "right": (0.0, v * h, (1 - u) * d),
        "left": (w, v * h, u * d),
        "back": ((1 - u) * w, v * h, d),
        "top": (u * w, 0.0, (1 - v) * d),
        "bottom": (u * w, h, v * d),
    }
    return folded[face]


_SIDE_MIDPOINTS: Mapping[Side, tuple[float, float]] = MappingProxyType(
    {"N": (0.5, 0.0), "S": (0.5, 1.0), "W": (0.0, 0.5), "E": (1.0, 0.5)}
)


def _tab_labels(placed: PlacedBox) -> list[tuple[str, Vec3]]:
    code = PART_CODES[placed.part]
    out: list[tuple[str, Vec3]] = []
    for tab in TABS:
        if tab.face not in VISIBLE_FACES and tab.mate_face not in VISIBLE_FACES:
            continue
        u, v = _SIDE_MIDPOINTS[tab.side]
        bx, by, bz = _net_to_box(placed.box, tab.face, u, v)
        ox, oy, oz = placed.origin
        out.append((f"{code}-{tab.letter}", (ox + bx, oy + by, oz + bz)))
    return out


def _depth(placed: PlacedBox) -> float:
    x, y, z = placed.origin
    box = placed.box
    # Larger means farther from the viewer at front, right and top.
    return (x + box.w / 2) + (y + box.h / 2) + (z + box.d / 2)


GlueZone = tuple[PartId, FaceId]


LabelMode = Literal["none", "tabs", "codes"]


def _labels(boxes: tuple[PlacedBox, ...], mode: LabelMode) -> list[tuple[str, Vec3]]:
    if mode == "tabs":
        return [lbl for placed in boxes for lbl in _tab_labels(placed)]
    if mode == "codes":
        return [(PART_CODES[b.part], _top_center(b)) for b in boxes]
    return []


def _top_center(placed: PlacedBox) -> Vec3:
    x, y, z = placed.origin
    return x + placed.box.w / 2, y, z + placed.box.d / 2


def build_diagram(
    boxes: tuple[PlacedBox, ...],
    glue: tuple[GlueZone, ...] = (),
    labels: LabelMode = "none",
) -> DiagramSpec:
    """Project boxes isometrically, back to front, normalized to the origin."""
    ordered = sorted(boxes, key=_depth, reverse=True)
    faces = [
        (_face_corners(placed, face), _TONES[face]) for placed in ordered for face in VISIBLE_FACES
    ]
    by_part = {placed.part: placed for placed in boxes}
    zones = [_face_corners(by_part[part], face) for part, face in glue]
    points = [_project(p) for corners, _ in faces for p in corners]
    min_x, min_y = min(p.x for p in points), min(p.y for p in points)

    def shift(p: Vec3) -> Point2:
        q = _project(p)
        return Point2(q.x - min_x, q.y - min_y)

    return DiagramSpec(
        width=max(p.x for p in points) - min_x,
        height=max(p.y for p in points) - min_y,
        faces=tuple(DiagramPolygon(tuple(map(shift, c)), tone) for c, tone in faces),
        glue_zones=tuple(tuple(map(shift, c)) for c in zones),
        labels=tuple(DiagramLabel(text, shift(at)) for text, at in _labels(boxes, labels)),
    )


def assembled_boxes(model: Model, explode: float = 0.0) -> tuple[PlacedBox, ...]:
    """All parts at their assembled positions, optionally pulled apart."""
    slots = {s.part: s for s in _view_slots(model, "front")}
    body = part_box("body", model)
    out: list[PlacedBox] = []
    for part in PART_IDS:
        box, slot = part_box(part, model), slots[part]
        # Boxes are centered on the body in depth; the head overhangs front and back.
        z = (body.d - box.d) / 2
        dx, dy = _explode_offset(part, explode)
        out.append(PlacedBox(part, box, (slot.x + dx, slot.y + dy, z)))
    return tuple(out)


def _explode_offset(part: PartId, distance: float) -> tuple[float, float]:
    offsets: Mapping[PartId, tuple[float, float]] = {
        "head": (0.0, -distance),
        "body": (0.0, 0.0),
        "right_arm": (-distance, 0.0),
        "left_arm": (distance, 0.0),
        "right_leg": (0.0, distance),
        "left_leg": (0.0, distance),
    }
    return offsets[part]


# Steps

ASSEMBLY_GLUE: tuple[GlueZone, ...] = (
    ("body", "top"),
    ("body", "right"),
    ("left_arm", "right"),
    ("right_leg", "top"),
    ("left_leg", "top"),
)
"""Visible faces that are glued in the final step; hidden mates are named in the text."""


def _single(part: PartId, model: Model) -> tuple[PlacedBox, ...]:
    return (PlacedBox(part, part_box(part, model), (0.0, 0.0, 0.0)),)


def _limbs(model: Model) -> tuple[PlacedBox, ...]:
    limbs: tuple[PartId, ...] = ("right_arm", "left_arm", "right_leg", "left_leg")
    step = part_box("right_arm", model).w + EXPLODE_CELLS
    return tuple(
        PlacedBox(part, part_box(part, model), (i * step, 0.0, 0.0)) for i, part in enumerate(limbs)
    )


_STEPS: tuple[tuple[str, Callable[[Model], DiagramSpec]], ...] = (
    ("cut", lambda m: build_diagram(_single("head", m))),
    ("fold", lambda m: build_diagram(_single("head", m))),
    ("head", lambda m: build_diagram(_single("head", m), labels="tabs")),
    ("body", lambda m: build_diagram(_single("body", m), labels="tabs")),
    ("limbs", lambda m: build_diagram(_limbs(m), labels="codes")),
    (
        "assemble",
        lambda m: build_diagram(assembled_boxes(m, EXPLODE_CELLS), ASSEMBLY_GLUE, "codes"),
    ),
)


def build_steps(model: Model) -> tuple[Step, ...]:
    """The six assembly steps of tech.md §5.5 in order."""
    return tuple(
        Step(i, f"step.{name}.title", f"step.{name}.body", diagram(model))
        for i, (name, diagram) in enumerate(_STEPS, start=1)
    )
