"""Face detection on real photos (tech.md §5.2, §10.7)."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest

from real2block.domain.vision.face import FaceBox, FakeDetector, Point, YuNetDetector
from real2block.domain.vision.loader import RgbImage, configure_pillow, load_photo
from tests.helpers import FIXTURES

MODEL = Path(__file__).parents[1] / "models" / "face_detection_yunet_2023mar.onnx"
THRESHOLD = 0.8
PHOTOS = sorted((FIXTURES / "photos").glob("*.jpg"))


@pytest.fixture(scope="module")
def detector() -> YuNetDetector:
    configure_pillow()
    return YuNetDetector(MODEL, THRESHOLD)


def _photo(path: Path) -> RgbImage:
    return load_photo(path.read_bytes())


def test_there_are_enough_fixture_photos() -> None:
    # tech.md §10.7 asks for 3 to 5 licensed photos.
    assert 3 <= len(PHOTOS) <= 5
    assert (FIXTURES / "photos" / "LICENSES.md").is_file()


@pytest.mark.parametrize("path", PHOTOS, ids=lambda p: p.stem)
def test_finds_the_face_on_each_photo(detector: YuNetDetector, path: Path) -> None:
    image = _photo(path)
    faces = detector.detect(image)
    assert faces, "no face found"
    face = faces[0]
    height, width = image.shape[:2]
    assert face.score >= THRESHOLD
    assert face.x >= 0
    assert face.y >= 0
    assert face.x + face.w <= width
    assert face.y + face.h <= height


@pytest.mark.parametrize("path", PHOTOS, ids=lambda p: p.stem)
def test_landmarks_are_in_anatomical_order(detector: YuNetDetector, path: Path) -> None:
    face = detector.detect(_photo(path))[0]
    # The person's right eye and mouth corner are on the left of the image.
    assert face.right_eye.x < face.left_eye.x
    assert face.right_mouth.x < face.left_mouth.x
    eyes_y = max(face.right_eye.y, face.left_eye.y)
    assert eyes_y < face.nose.y < min(face.right_mouth.y, face.left_mouth.y)
    for point in (face.right_eye, face.left_eye, face.nose, face.right_mouth, face.left_mouth):
        assert face.x <= point.x <= face.x + face.w
        assert face.y <= point.y <= face.y + face.h


def test_blank_image_has_no_face(detector: YuNetDetector) -> None:
    assert detector.detect(np.full((512, 512, 3), 128, dtype=np.uint8)) == []


def test_concurrent_calls_match_sequential_ones(detector: YuNetDetector) -> None:
    # Different sizes force the shared detector to change its input size between calls.
    images = [_photo(path) for path in PHOTOS] * 4
    expected = [detector.detect(image) for image in images]
    with ThreadPoolExecutor(max_workers=8) as pool:
        actual = list(pool.map(detector.detect, images))
    assert actual == expected


def test_fake_detector_returns_its_faces() -> None:
    p = Point(1, 1)
    face = FaceBox(0, 0, 10, 10, 0.9, p, p, p, p, p)
    assert FakeDetector([face]).detect(np.zeros((4, 4, 3), dtype=np.uint8)) == [face]
    assert FakeDetector().detect(np.zeros((4, 4, 3), dtype=np.uint8)) == []
