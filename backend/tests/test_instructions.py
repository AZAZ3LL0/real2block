"""Cover views and assembly steps from tech.md §4.1 and §5.5."""

import pytest

from real2block.domain.papercraft.instructions import (
    ASSEMBLY_GLUE,
    DiagramSpec,
    Point2,
    build_cover,
    build_steps,
    figure_view,
)
from real2block.domain.papercraft.strings import text
from real2block.domain.skin.geometry import FaceId, Model, PartId, face_rect
from real2block.domain.skin.skin import Skin


def _view_pixel(skin: Skin, model: Model, side: FaceId, x: int, y: int) -> tuple[int, int, int]:
    view = figure_view(skin, model, "front" if side == "front" else "back")
    cell = next(c for c in view.cells if (c.x, c.y) == (x, y))
    return cell.color.r, cell.color.g, cell.color.b


def _face_pixel(skin: Skin, part: PartId, face: FaceId, model: Model) -> tuple[int, int, int]:
    rect = face_rect(part, face, model=model)
    color = skin.rgb_at(rect.x, rect.y)
    return color.r, color.g, color.b


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        # The figure's right side is on the viewer's left from the front (tech.md §4.1).
        ("classic", {"right_arm": (0, 8), "head": (4, 0), "body": (4, 8), "left_arm": (12, 8)}),
        ("slim", {"right_arm": (0, 8), "head": (3, 0), "body": (3, 8), "left_arm": (11, 8)}),
    ],
)
def test_front_view_top_left_corners(
    reference_skin: Skin, model: Model, expected: dict[PartId, tuple[int, int]]
) -> None:
    legs: dict[PartId, tuple[int, int]] = {
        "right_leg": (expected["body"][0], 20),
        "left_leg": (expected["body"][0] + 4, 20),
    }
    for part, (x, y) in {**expected, **legs}.items():
        assert _view_pixel(reference_skin, model, "front", x, y) == _face_pixel(
            reference_skin, part, "front", model
        )


def test_back_view_mirrors_sides(reference_skin: Skin) -> None:
    corners: dict[PartId, tuple[int, int]] = {
        "left_arm": (0, 8),
        "head": (4, 0),
        "body": (4, 8),
        "right_arm": (12, 8),
        "left_leg": (4, 20),
        "right_leg": (8, 20),
    }
    for part, (x, y) in corners.items():
        assert _view_pixel(reference_skin, "classic", "back", x, y) == _face_pixel(
            reference_skin, part, "back", "classic"
        )


@pytest.mark.parametrize(("model", "cols"), [("classic", 16), ("slim", 14)])
def test_view_covers_every_face_pixel_once(reference_skin: Skin, model: Model, cols: int) -> None:
    view = figure_view(reference_skin, model, "front")
    positions = [(c.x, c.y) for c in view.cells]
    assert (view.cols, view.rows) == (cols, 32)
    assert len(positions) == len(set(positions))
    # head 8x8 + body 8x12 + two arms + two legs 4x12
    arm = 4 if model == "classic" else 3
    assert len(positions) == 64 + 96 + 2 * arm * 12 + 2 * 48
    assert all(0 <= x < view.cols and 0 <= y < view.rows for x, y in positions)


@pytest.mark.parametrize(
    ("model", "pixel_mm", "size"),
    [("classic", 5.0, (80.0, 160.0, 40.0)), ("slim", 4.0, (56.0, 128.0, 32.0))],
)
def test_cover_size_and_parts(
    reference_skin: Skin, model: Model, pixel_mm: float, size: tuple[float, float, float]
) -> None:
    cover = build_cover(reference_skin, model, pixel_mm)
    assert (cover.size.width, cover.size.height, cover.size.depth) == pytest.approx(size)
    assert cover.parts == ("head", "body", "right_arm", "left_arm", "right_leg", "left_leg")
    assert len(cover.tool_keys) == 4


def test_six_steps_in_spec_order() -> None:
    steps = build_steps("classic")
    assert [s.index for s in steps] == [1, 2, 3, 4, 5, 6]
    names = [s.title_key.split(".")[1] for s in steps]
    assert names == ["cut", "fold", "head", "body", "limbs", "assemble"]
    for step in steps:
        for lang in ("ru", "en"):
            assert text(lang, step.title_key)
            assert text(lang, step.body_key)


def test_glue_order_text_names_seam_top_bottom() -> None:
    body = text("en", build_steps("classic")[2].body_key)
    assert body.index("H-G") < body.index("H-A") < body.index("H-D")


def _labels(diagram: DiagramSpec) -> dict[str, Point2]:
    return {label.text: label.at for label in diagram.labels}


def _on_segment(p: Point2, a: Point2, b: Point2) -> bool:
    cross = (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x)
    within = min(a.x, b.x) - 1e-9 <= p.x <= max(a.x, b.x) + 1e-9
    return abs(cross) < 1e-9 and within


def _edges(diagram: DiagramSpec, tone: str) -> list[tuple[Point2, Point2]]:
    poly = next(f.points for f in diagram.faces if f.tone == tone)
    return list(zip(poly, poly[1:] + poly[:1], strict=True))


def test_head_tab_labels_sit_on_their_edges() -> None:
    diagram = build_steps("classic")[2].diagram
    labels = _labels(diagram)
    # Bottom-face tabs E and F are on hidden edges.
    assert set(labels) == {"H-A", "H-B", "H-C", "H-D", "H-G"}
    top, side = _edges(diagram, "top"), _edges(diagram, "side")
    shared = [e for e in top if any({*e} == {*s} for s in side)]
    # A joins top and the figure's right side; G is the right side's seam with the back.
    assert _on_segment(labels["H-A"], *shared[0])
    assert any(_on_segment(labels["H-G"], *e) for e in side)
    assert labels["H-G"].x == pytest.approx(min(p.x for e in side for p in e))
    for letter in "BC":
        assert any(_on_segment(labels[f"H-{letter}"], *e) for e in top)


def test_assembly_frames_glue_zones() -> None:
    diagram = build_steps("classic")[5].diagram
    assert len(diagram.glue_zones) == len(ASSEMBLY_GLUE) == 5
    faces = {tuple(f.points) for f in diagram.faces}
    assert all(tuple(zone) in faces for zone in diagram.glue_zones)
    assert {label.text for label in diagram.labels} == {"H", "B", "RA", "LA", "RL", "LL"}


def test_diagram_is_normalized() -> None:
    for step in build_steps("slim"):
        points = [p for f in step.diagram.faces for p in f.points]
        assert min(p.x for p in points) == pytest.approx(0.0)
        assert min(p.y for p in points) == pytest.approx(0.0)
        assert max(p.x for p in points) == pytest.approx(step.diagram.width)
        assert max(p.y for p in points) == pytest.approx(step.diagram.height)
