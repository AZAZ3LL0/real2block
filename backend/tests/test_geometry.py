"""UV layout from tech.md §4.1: exact table values and layout invariants."""

from hypothesis import given
from hypothesis import strategies as st

from real2block.domain.skin.geometry import (
    FACE_IDS,
    LAYERS,
    PART_IDS,
    PARTS,
    BoxSpec,
    Model,
    Rect,
    face_rect,
    uv_rect,
)

MODELS: tuple[Model, ...] = ("classic", "slim")
sizes = st.integers(min_value=1, max_value=16)


def test_head_faces_match_minecraft_layout() -> None:
    expected = {
        "top": Rect(8, 0, 8, 8),
        "bottom": Rect(16, 0, 8, 8),
        "right": Rect(0, 8, 8, 8),
        "front": Rect(8, 8, 8, 8),
        "left": Rect(16, 8, 8, 8),
        "back": Rect(24, 8, 8, 8),
    }
    assert {f: face_rect("head", f) for f in FACE_IDS} == expected


def test_body_and_slim_arm_faces() -> None:
    assert face_rect("body", "front") == Rect(20, 20, 8, 12)
    assert face_rect("body", "back") == Rect(32, 20, 8, 12)
    assert face_rect("right_arm", "front", model="slim") == Rect(44, 20, 3, 12)
    assert face_rect("right_arm", "back", model="slim") == Rect(51, 20, 3, 12)
    assert face_rect("left_arm", "top", "overlay", "classic") == Rect(52, 48, 4, 4)
    assert face_rect("left_leg", "front", "overlay") == Rect(4, 52, 4, 12)


def test_table_origins() -> None:
    classic = PARTS["classic"]
    assert classic["head"].overlay == (32, 0)
    assert classic["body"].base == (16, 16)
    assert classic["right_leg"].overlay == (0, 32)
    assert classic["left_arm"].base == (32, 48)
    assert PARTS["slim"]["left_arm"].box == BoxSpec(3, 12, 4)


@given(sizes, sizes, sizes)
def test_faces_tile_area_without_overlap(w: int, h: int, d: int) -> None:
    box = BoxSpec(w, h, d)
    cells = [c for f in FACE_IDS for c in uv_rect(box, (0, 0), f).cells()]
    assert len(cells) == 2 * (w * h + w * d + h * d)
    assert len(set(cells)) == len(cells)


def test_every_rect_inside_texture() -> None:
    for model in MODELS:
        for layer in LAYERS:
            for part in PART_IDS:
                for face in FACE_IDS:
                    r = face_rect(part, face, layer, model)
                    assert min(r.x, r.y) >= 0
                    assert max(r.x + r.w, r.y + r.h) <= 64


def test_parts_of_one_layer_do_not_intersect() -> None:
    for model in MODELS:
        for layer in LAYERS:
            seen: set[tuple[int, int]] = set()
            for part in PART_IDS:
                cells = {c for f in FACE_IDS for c in face_rect(part, f, layer, model).cells()}
                assert not seen & cells, (model, layer, part)
                seen |= cells
