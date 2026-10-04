"""Box nets from tech.md §4.2-4.3: golden rasters, orientation, tabs, sizes."""

from collections import Counter

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from real2block.domain.papercraft.net import (
    NetFace,
    NetPart,
    NetTab,
    Point,
    box_cell_map,
    build_net_part,
    net_cell_map,
    net_faces,
    render_debug_png,
)
from real2block.domain.skin.geometry import (
    FACE_IDS,
    PART_IDS,
    BoxSpec,
    Model,
    PartId,
    face_rect,
    part_box,
    uv_rect,
)
from real2block.domain.skin.skin import Skin
from tests.helpers import FIXTURES, decode_png

sizes = st.integers(min_value=1, max_value=16)


@pytest.mark.parametrize("part", PART_IDS)
def test_golden_net(reference_skin: Skin, part: PartId) -> None:
    golden = (FIXTURES / f"reference_net_{part}.png").read_bytes()
    actual = render_debug_png(reference_skin, part, "classic")
    np.testing.assert_array_equal(decode_png(actual), decode_png(golden))


@given(sizes, sizes, sizes)
def test_net_area_and_one_to_one_mapping(w: int, h: int, d: int) -> None:
    box = BoxSpec(w, h, d)
    mapping = box_cell_map(box, (0, 0))
    texture = {c for f in FACE_IDS for c in uv_rect(box, (0, 0), f).cells()}
    assert len(mapping) == 2 * (w * h + w * d + h * d)
    assert len(set(mapping.values())) == len(mapping)
    assert set(mapping.values()) == texture


@given(sizes, sizes, sizes)
def test_net_faces_do_not_overlap(w: int, h: int, d: int) -> None:
    cells = [c for p in net_faces(BoxSpec(w, h, d)) for c in p.rect.cells()]
    assert len(cells) == len(set(cells))


def test_cross_arrangement() -> None:
    faces = {p.face: p.rect for p in net_faces(BoxSpec(8, 12, 4))}
    front = faces["front"]
    assert (faces["top"].x, faces["top"].y + faces["top"].h) == (front.x, front.y)
    assert (faces["bottom"].x, faces["bottom"].y) == (front.x, front.y + front.h)
    assert faces["right"].x + faces["right"].w == front.x
    assert faces["left"].x == front.x + front.w
    assert faces["back"].x == faces["left"].x + faces["left"].w


def test_top_as_is_and_bottom_flipped() -> None:
    box = BoxSpec(8, 8, 8)
    faces = {p.face: p for p in net_faces(box)}
    mapping = box_cell_map(box, (0, 0))
    top, bottom = faces["top"].rect, faces["bottom"].rect
    top_tex, bottom_tex = uv_rect(box, (0, 0), "top"), uv_rect(box, (0, 0), "bottom")
    # Row 0 of top texture is the far edge (shared with back).
    assert mapping[(top.x, top.y)] == (top_tex.x, top_tex.y)
    # Bottom is mirrored vertically: texture row 0 lands on the far edge of the net.
    assert mapping[(bottom.x, bottom.y + bottom.h - 1)] == (bottom_tex.x, bottom_tex.y)
    assert mapping[(bottom.x, bottom.y)] == (bottom_tex.x, bottom_tex.y + bottom_tex.h - 1)


@pytest.mark.parametrize(
    ("part", "size"),
    [
        ("head", (166.0, 132.0)),
        ("body", (126.0, 112.0)),
        ("right_arm", (86.0, 112.0)),
        ("left_arm", (86.0, 112.0)),
        ("right_leg", (86.0, 112.0)),
        ("left_leg", (86.0, 112.0)),
    ],
)
def test_part_size_at_5mm(reference_skin: Skin, part: PartId, size: tuple[float, float]) -> None:
    net = build_net_part(reference_skin, part, "classic", 5.0)
    assert (net.width, net.height) == pytest.approx(size)


def test_seven_tabs_with_labels(reference_skin: Skin) -> None:
    net = build_net_part(reference_skin, "left_leg", "classic", 5.0)
    assert [t.label.text for t in net.tabs] == [f"LL-{c}" for c in "ABCDEFG"]
    assert [lbl.text for lbl in net.edge_labels] == [f"LL-{c}" for c in "ABCDEFG"]
    assert len(net.cut) == 7 * 3 + 7
    assert len(net.fold) == 5 + 7


def test_tabs_are_45_degree_trapezoids(reference_skin: Skin) -> None:
    net = build_net_part(reference_skin, "head", "classic", 5.0)
    for tab in net.tabs:
        p0, q0, q1, p1 = tab.polygon
        for a, b in ((p0, q0), (p1, q1)):
            assert abs(a.x - b.x) == pytest.approx(6.0)
            assert abs(a.y - b.y) == pytest.approx(6.0)


def test_net_inside_bounding_box(reference_skin: Skin) -> None:
    net = build_net_part(reference_skin, "head", "classic", 5.0)
    points = [p for seg in net.cut + net.fold for p in seg]
    assert min(p.x for p in points) == pytest.approx(0.0)
    assert min(p.y for p in points) == pytest.approx(0.0)
    assert max(p.x for p in points) == pytest.approx(net.width)
    assert max(p.y for p in points) == pytest.approx(net.height)


@pytest.mark.parametrize("part", PART_IDS)
def test_cell_colors_round_trip(reference_skin: Skin, part: PartId) -> None:
    pixel_mm = 4.0
    net = build_net_part(reference_skin, part, "classic", pixel_mm)
    faces = {f.face: f for f in net.faces}
    by_pos = {(round(c.x, 6), round(c.y, 6)): c.color for c in net.cells}
    for face_id in FACE_IDS:
        face, tex = faces[face_id], face_rect(part, face_id)
        for j in range(face.rows):
            for i in range(face.cols):
                row = tex.h - 1 - j if face_id == "bottom" else j
                key = (round(face.x + i * pixel_mm, 6), round(face.y + j * pixel_mm, 6))
                assert by_pos[key] == reference_skin.rgb_at(tex.x + i, tex.y + row)


# Folding: every tab must meet the edge carrying the same label on the assembled box.

Vec3 = tuple[float, float, float]
PIXEL_SIZES = (3.0, 4.0, 5.0, 6.5, 8.0)
CASES = [(part, model) for part in PART_IDS for model in ("classic", "slim")]


def _fold(face: NetFace, box: BoxSpec, p: Point) -> Vec3:
    # Box frame: x from the figure's right side, y down from the top, z from front to back.
    u = (p.x - face.x) / (face.cols * face.cell)
    v = (p.y - face.y) / (face.rows * face.cell)
    w, h, d = box.w, box.h, box.d
    positions: dict[str, Vec3] = {
        "front": (u * w, v * h, 0.0),
        "right": (0.0, v * h, (1 - u) * d),
        "left": (w, v * h, u * d),
        "back": ((1 - u) * w, v * h, d),
        "top": (u * w, 0.0, (1 - v) * d),
        "bottom": (u * w, h, v * d),
    }
    x, y, z = positions[face.face]
    return round(x, 6), round(y, 6), round(z, 6)


def _on_boundary(face: NetFace, p: Point) -> bool:
    right, bottom = face.x + face.cols * face.cell, face.y + face.rows * face.cell
    inside = face.x - 1e-9 <= p.x <= right + 1e-9 and face.y - 1e-9 <= p.y <= bottom + 1e-9
    edge = min(abs(p.x - face.x), abs(p.x - right), abs(p.y - face.y), abs(p.y - bottom))
    return inside and edge < 1e-9


def _face_of(net: NetPart, a: Point, b: Point) -> NetFace | None:
    mid = Point((a.x + b.x) / 2, (a.y + b.y) / 2)
    faces = [f for f in net.faces if all(_on_boundary(f, p) for p in (a, b, mid))]
    return faces[0] if len(faces) == 1 else None


def _edge_3d(net: NetPart, box: BoxSpec, a: Point, b: Point) -> frozenset[Vec3] | None:
    face = _face_of(net, a, b)
    return None if face is None else frozenset({_fold(face, box, a), _fold(face, box, b)})


@pytest.mark.parametrize(("part", "model"), CASES)
@pytest.mark.parametrize("pixel_mm", PIXEL_SIZES)
def test_tabs_meet_labelled_mate_edge(
    reference_skin: Skin, part: PartId, model: Model, pixel_mm: float
) -> None:
    net = build_net_part(reference_skin, part, model, pixel_mm)
    box = part_box(part, model)
    labels = {lbl.text: lbl for lbl in net.edge_labels}
    for tab in net.tabs:
        base = _edge_3d(net, box, tab.polygon[0], tab.polygon[3])
        assert base is not None
        mates = [(a, b) for a, b in net.cut if _edge_3d(net, box, a, b) == base]
        assert len(mates) == 1, tab.label.text
        (a, b), label = mates[0], labels[tab.label.text]
        mate_face = _face_of(net, a, b)
        assert mate_face is not None
        assert _point_in_face(mate_face, label.at)
        distance = abs(label.at.x - a.x) if a.x == b.x else abs(label.at.y - a.y)
        assert distance <= pixel_mm


def _point_in_face(face: NetFace, p: Point) -> bool:
    return (
        face.x < p.x < face.x + face.cols * face.cell
        and face.y < p.y < face.y + face.rows * face.cell
    )


@pytest.mark.parametrize(("part", "model"), CASES)
@pytest.mark.parametrize("pixel_mm", PIXEL_SIZES)
def test_cut_outline_is_closed(
    reference_skin: Skin, part: PartId, model: Model, pixel_mm: float
) -> None:
    net = build_net_part(reference_skin, part, model, pixel_mm)
    degree = Counter((round(p.x, 6), round(p.y, 6)) for segment in net.cut for p in segment)
    assert set(degree.values()) == {2}


@pytest.mark.parametrize(("part", "model"), CASES)
@pytest.mark.parametrize("pixel_mm", PIXEL_SIZES)
def test_tabs_stay_off_faces_and_each_other(
    reference_skin: Skin, part: PartId, model: Model, pixel_mm: float
) -> None:
    net = build_net_part(reference_skin, part, model, pixel_mm)
    boxes = [_bounds(t.polygon) for t in net.tabs]
    boxes += [(f.x, f.y, f.x + f.cols * f.cell, f.y + f.rows * f.cell) for f in net.faces]
    for i, first in enumerate(boxes[: len(net.tabs)]):
        for second in boxes[i + 1 :]:
            assert _overlap_area(first, second) == pytest.approx(0.0)


def _bounds(points: tuple[Point, ...]) -> tuple[float, float, float, float]:
    xs, ys = [p.x for p in points], [p.y for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _overlap_area(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(w, 0.0) * max(h, 0.0)


def _tab_is_trapezoid(tab: NetTab) -> bool:
    p0, q0, q1, p1 = tab.polygon
    base = (p1.x - p0.x, p1.y - p0.y)
    top = (q1.x - q0.x, q1.y - q0.y)
    # The free side must run the same way as the base, otherwise the slopes cross.
    return base[0] * top[0] + base[1] * top[1] >= 0


@pytest.mark.parametrize(("part", "model"), CASES)
@pytest.mark.parametrize("pixel_mm", PIXEL_SIZES)
def test_tab_sides_do_not_cross(
    reference_skin: Skin, part: PartId, model: Model, pixel_mm: float
) -> None:
    if model == "slim" and part.endswith("arm") and pixel_mm < 4.0:
        pytest.xfail("slim arm edge is shorter than two 45-degree slopes; open contract gap")
    net = build_net_part(reference_skin, part, model, pixel_mm)
    assert all(_tab_is_trapezoid(tab) for tab in net.tabs)


@pytest.mark.parametrize("part", ["right_arm", "left_arm"])
def test_slim_debug_raster_matches_cell_map(reference_skin: Skin, part: PartId) -> None:
    raster = decode_png(render_debug_png(reference_skin, part, "slim"))
    assert raster.shape[:2] == (2 * 4 + 12, 2 * 4 + 2 * 3)
    mapping = net_cell_map(part, "slim")
    for (x, y), (u, v) in mapping.items():
        np.testing.assert_array_equal(raster[y, x], reference_skin.pixels[v, u])
    assert int((raster[..., 3] > 0).sum()) <= len(mapping)
