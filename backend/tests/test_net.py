"""Box nets from tech.md §4.2-4.3: golden rasters, orientation, tabs, sizes."""

import io

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from PIL import Image

from real2block.domain.papercraft.net import (
    box_cell_map,
    build_net_part,
    net_faces,
    render_debug_png,
)
from real2block.domain.skin.geometry import FACE_IDS, PART_IDS, BoxSpec, PartId, face_rect, uv_rect
from real2block.domain.skin.skin import Skin
from tests.helpers import FIXTURES

sizes = st.integers(min_value=1, max_value=16)


def _decode(data: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as img:
        return np.asarray(img.convert("RGBA"))


@pytest.mark.parametrize("part", PART_IDS)
def test_golden_net(reference_skin: Skin, part: PartId) -> None:
    golden = (FIXTURES / f"reference_net_{part}.png").read_bytes()
    actual = render_debug_png(reference_skin, part, "classic")
    np.testing.assert_array_equal(_decode(actual), _decode(golden))


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
