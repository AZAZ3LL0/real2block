"""PhotoAnalyzer with FakeDetector on synthetic photos (tech.md §5.2, §10.6)."""

from dataclasses import replace

import pytest

from real2block.domain.color import Rgb, delta_e, to_lab
from real2block.domain.errors import NoFaceError
from real2block.domain.vision.analyzer import (
    DEFAULT_EYE_WHITE,
    DEFAULT_HAIR,
    DEFAULT_IRIS,
    DEFAULT_PANTS,
    DEFAULT_SHIRT,
    DEFAULT_SHOES,
    AnalyzeResult,
    PhotoAnalyzer,
)
from real2block.domain.vision.face import FaceBox, FakeDetector, Point
from real2block.domain.vision.loader import configure_pillow
from tests.helpers import png_bytes
from tests.portrait import Portrait

MAX_DELTA_E = 5.0


@pytest.fixture(autouse=True)
def _pillow_guard() -> None:
    configure_pillow()


def _analyze(scene: Portrait, decoys: tuple[FaceBox, ...] = ()) -> AnalyzeResult:
    """Analyze the rendered scene; decoy boxes come first, as a detector may order them."""
    faces = [*decoys, scene.box()]
    return PhotoAnalyzer(FakeDetector(faces)).analyze(png_bytes(scene.render()))


def _close(a: Rgb, b: Rgb) -> bool:
    return delta_e(to_lab([a])[0], to_lab([b])[0]) <= MAX_DELTA_E


def test_sampled_roles_match_the_drawn_colors() -> None:
    scene = Portrait()
    result = _analyze(scene)
    palette = result.spec.palette
    for role in ("skin", "hair", "iris", "mouth", "shirt"):
        assert _close(getattr(palette, role), getattr(scene, role)), role
    assert result.warnings == ()


def test_unsampled_roles_get_the_defaults() -> None:
    palette = _analyze(Portrait()).spec.palette
    assert (palette.pants, palette.shoes, palette.eye_white) == (
        DEFAULT_PANTS,
        DEFAULT_SHOES,
        DEFAULT_EYE_WHITE,
    )


def test_spec_starts_from_the_template_defaults() -> None:
    spec = _analyze(Portrait()).spec
    assert (spec.model, spec.stylizer, spec.hair_style) == ("classic", "template", "short")


def test_no_face_is_an_error() -> None:
    with pytest.raises(NoFaceError):
        PhotoAnalyzer(FakeDetector()).analyze(png_bytes(Portrait().render()))


def _analyze_box(scene: Portrait, face: FaceBox) -> AnalyzeResult:
    return PhotoAnalyzer(FakeDetector([face])).analyze(png_bytes(scene.render()))


def test_face_outside_the_frame_is_no_face() -> None:
    # Detectors report partly visible faces; with both cheeks off frame there is no skin.
    scene = Portrait()
    face = scene.box()
    off = -2.0 * scene.width

    def move(p: Point) -> Point:
        return Point(p.x + off, p.y)

    gone = replace(
        face,
        x=face.x + off,
        right_eye=move(face.right_eye),
        left_eye=move(face.left_eye),
        nose=move(face.nose),
        right_mouth=move(face.right_mouth),
        left_mouth=move(face.left_mouth),
    )
    with pytest.raises(NoFaceError):
        _analyze_box(scene, gone)


def test_eyes_above_the_frame_get_the_default_iris() -> None:
    scene = Portrait()
    face = scene.box()
    y = -0.1 * face.w
    cut = replace(
        face,
        right_eye=Point(face.right_eye.x, y),
        left_eye=Point(face.left_eye.x, y),
    )
    assert _analyze_box(scene, cut).spec.palette.iris == DEFAULT_IRIS


def test_swapped_mouth_corners_keep_the_mouth_color() -> None:
    scene = Portrait()
    face = scene.box()
    swapped = replace(face, right_mouth=face.left_mouth, left_mouth=face.right_mouth)
    assert _close(_analyze_box(scene, swapped).spec.palette.mouth, scene.mouth)


def test_torso_off_frame_keeps_the_default_shirt() -> None:
    result = _analyze(Portrait(face=(300, 650, 200, 240)))
    assert "TORSO_NOT_VISIBLE" in result.warnings
    assert result.spec.palette.shirt == DEFAULT_SHIRT


def test_hair_in_the_background_color_is_not_detected() -> None:
    color = Rgb(0x30, 0x22, 0x18)
    result = _analyze(Portrait(background=color, hair=color))
    assert "HAIR_NOT_DETECTED" in result.warnings
    assert result.spec.hair_style == "bald"
    assert result.spec.palette.hair == DEFAULT_HAIR


def test_long_hair_is_recognized() -> None:
    assert _analyze(Portrait(long_hair=True)).spec.hair_style == "long"


def test_the_largest_of_several_faces_is_used() -> None:
    scene = Portrait()
    decoy = Portrait(face=(40, 40, 80, 96)).box()
    result = _analyze(scene, (decoy,))
    assert "MULTIPLE_FACES" in result.warnings
    assert _close(result.spec.palette.skin, scene.skin)


def test_small_face_is_reported() -> None:
    assert "FACE_TOO_SMALL" in _analyze(Portrait(face=(370, 300, 60, 72))).warnings


def test_dark_face_is_reported() -> None:
    assert "LOW_LIGHT" in _analyze(Portrait(skin=Rgb(0x30, 0x22, 0x1A))).warnings


def test_face_front_is_8x8_with_at_most_6_colors() -> None:
    face = _analyze(Portrait()).spec.face_front
    assert face is not None
    assert [len(row) for row in face] == [8] * 8
    assert len({color for row in face for color in row}) <= 6


def test_same_photo_gives_the_same_spec() -> None:
    assert _analyze(Portrait()) == _analyze(Portrait())
