"""Color sampling on synthetic portraits (tech.md §5.2 step 3, §10.6)."""

from dataclasses import replace

import numpy as np
import pytest

from real2block.domain.color import Rgb, delta_e, to_lab
from real2block.domain.vision.face import FaceBox, Point
from real2block.domain.vision.sampling import (
    Rect,
    background_lab,
    clusters,
    face_lightness,
    hair_lab,
    hair_share_below_mouth,
    iris_lab,
    mouth_lab,
    shirt_lab,
    skin_lab,
)
from tests.portrait import Portrait

MAX_DELTA_E = 5.0


def _close(lab: np.ndarray | None, color: Rgb) -> bool:
    return lab is not None and delta_e(lab, to_lab([color])[0]) <= MAX_DELTA_E


def _sample_all(scene: Portrait) -> dict[str, np.ndarray | None]:
    image, face = scene.render(), scene.box()
    skin, bg = skin_lab(image, face), background_lab(image)
    return {
        "skin": skin,
        "iris": iris_lab(image, face),
        "mouth": mouth_lab(image, face),
        "background": bg,
        "hair": hair_lab(image, face, skin, bg),
        "shirt": shirt_lab(image, face, skin),
    }


def test_every_role_matches_the_drawn_color() -> None:
    scene = Portrait()
    found = _sample_all(scene)
    for role in ("skin", "iris", "mouth", "background", "hair", "shirt"):
        assert _close(found[role], getattr(scene, role)), role


@pytest.mark.parametrize(
    "skin",
    [Rgb(0xF1, 0xC2, 0xA4), Rgb(0x8D, 0x5A, 0x3B), Rgb(0x4A, 0x2E, 0x22)],
    ids=["light", "medium", "dark"],
)
def test_skin_tone_range(skin: Rgb) -> None:
    scene = Portrait(skin=skin)
    assert _close(_sample_all(scene)["skin"], skin)


def test_dark_iris_wins_over_light_eye_white() -> None:
    scene = Portrait(iris=Rgb(0x6B, 0x8E, 0x23), eye_white=Rgb(0xFF, 0xFF, 0xFF))
    assert _close(_sample_all(scene)["iris"], scene.iris)


def test_background_in_hair_color_is_not_taken_for_hair() -> None:
    # Short, tight hair leaves the sampled strips mostly background, the largest cluster.
    scene = Portrait(
        background=Rgb(0x20, 0x20, 0x20), hair=Rgb(0xC8, 0x8A, 0x3C), hair_margin=0.0, hair_top=0.15
    )
    assert _close(_sample_all(scene)["hair"], scene.hair)


def test_hair_matching_the_background_is_not_detected() -> None:
    scene = Portrait(background=Rgb(0x30, 0x22, 0x18), hair=Rgb(0x30, 0x22, 0x18))
    assert _sample_all(scene)["hair"] is None


def test_bald_head_has_no_hair() -> None:
    assert _sample_all(Portrait(hair=None))["hair"] is None


def test_face_at_the_bottom_hides_the_torso() -> None:
    # The shirt box is only ~16% inside the frame, and that strip is all shirt.
    scene = Portrait(face=(300, 650, 200, 240))
    assert _sample_all(scene)["shirt"] is None


def test_mostly_visible_torso_is_sampled() -> None:
    scene = Portrait(face=(300, 450, 200, 240))
    assert _close(_sample_all(scene)["shirt"], scene.shirt)


def test_shirt_in_skin_color_is_not_taken_for_the_shirt() -> None:
    scene = Portrait(shirt=Rgb(0xC6, 0x8E, 0x6A))
    shirt = _sample_all(scene)["shirt"]
    assert not _close(shirt, scene.shirt)


def test_long_hair_covers_the_strips_below_the_mouth() -> None:
    hair = Portrait().hair
    assert hair is not None
    lab = to_lab([hair])[0]
    for long_hair, expected in ((True, True), (False, False)):
        scene = Portrait(long_hair=long_hair)
        share = hair_share_below_mouth(scene.render(), scene.box(), lab)
        assert (share > 0.4) is expected, share


def test_face_lightness_tracks_exposure() -> None:
    bright = Portrait()
    dark = replace(bright, skin=Rgb(0x30, 0x22, 0x1A))
    assert (
        face_lightness(dark.render(), dark.box())
        < 25
        < face_lightness(bright.render(), bright.box())
    )


def test_clusters_are_deterministic_and_sorted_by_size() -> None:
    rng = np.random.default_rng(1)
    lab = rng.normal(size=(500, 3)).astype(np.float32) * 10
    first, second = clusters(lab, 3), clusters(lab, 3)
    assert [c.size for c in first] == sorted((c.size for c in first), reverse=True)
    assert all(np.array_equal(a.center, b.center) for a, b in zip(first, second, strict=True))
    assert 1 <= len(clusters(lab[:2], 3)) <= 2
    assert clusters(lab[:0], 3) == []


def test_regions_off_frame_are_clipped() -> None:
    assert Rect(-10, -10, 10, 10).clip(5, 5) == Rect(0, 0, 5, 5)
    assert Rect(10, 10, 20, 20).clip(5, 5).area == 0


def test_swapped_mouth_corners_still_sample_the_mouth() -> None:
    # A turned head can make the detector report the corners in either order.
    scene = Portrait()
    face = scene.box()
    swapped = replace(face, right_mouth=face.left_mouth, left_mouth=face.right_mouth)
    assert _close(mouth_lab(scene.render(), swapped), scene.mouth)


def _off_frame(face: FaceBox, dx: float) -> FaceBox:
    def move(p: Point) -> Point:
        return Point(p.x + dx, p.y)

    return replace(
        face,
        x=face.x + dx,
        right_eye=move(face.right_eye),
        left_eye=move(face.left_eye),
        nose=move(face.nose),
        right_mouth=move(face.right_mouth),
        left_mouth=move(face.left_mouth),
    )


def test_regions_outside_the_frame_give_no_color() -> None:
    scene = Portrait()
    face = _off_frame(scene.box(), -2 * scene.width)
    image = scene.render()
    assert skin_lab(image, face) is None
    assert iris_lab(image, face) is None
    assert mouth_lab(image, face) is None
