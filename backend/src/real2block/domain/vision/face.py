"""Face detection: model integrity check, YuNet and a fake for tests (tech.md §5.2, §8.2)."""

import hashlib
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
import numpy.typing as npt

from real2block.domain.vision.loader import RgbImage

YUNET_INPUT_SIZE = (320, 320)
SHA256SUMS_NAME = "SHA256SUMS"
_CHUNK = 1 << 16


class ModelIntegrityError(RuntimeError):
    """Model file is missing or its SHA-256 does not match; the app must not start."""


def expected_sha256(model_path: Path) -> str:
    """Look up the model checksum in SHA256SUMS next to the model file."""
    sums = model_path.parent / SHA256SUMS_NAME
    if not sums.is_file():
        raise ModelIntegrityError(f"{sums} not found")
    for line in sums.read_text().splitlines():
        digest, _, name = line.strip().partition("  ")
        if name == model_path.name:
            return digest.lower()
    raise ModelIntegrityError(f"{model_path.name} is not listed in {sums}")


def file_sha256(path: Path) -> str:
    """Hex SHA-256 of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def verify_model(model_path: Path) -> None:
    """Raise if the model is missing or tampered with."""
    if not model_path.is_file():
        raise ModelIntegrityError(f"{model_path} not found")
    if file_sha256(model_path) != expected_sha256(model_path):
        raise ModelIntegrityError(f"{model_path.name} checksum mismatch")


@dataclass(frozen=True, slots=True)
class Point:
    """Image point in pixels."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class FaceBox:
    """Face position and five landmarks; nothing that could identify a person (tech.md §8.1)."""

    x: float
    y: float
    w: float
    h: float
    score: float
    right_eye: Point
    left_eye: Point
    nose: Point
    right_mouth: Point
    left_mouth: Point

    @property
    def area(self) -> float:
        """Box area in square pixels."""
        return self.w * self.h


class FaceDetector(Protocol):
    """Finds faces on an upright RGB image."""

    def detect(self, image: RgbImage) -> list[FaceBox]:
        """Faces with score at or above the configured threshold."""
        ...


# One YuNet output row: box (4), five landmarks as x, y pairs (10), score (1).
_BOX = slice(0, 4)
_LANDMARKS = slice(4, 14)
_SCORE = 14


def _face_from_row(row: npt.NDArray[np.float32]) -> FaceBox:
    x, y, w, h = (float(v) for v in row[_BOX])
    coords = [float(v) for v in row[_LANDMARKS]]
    # YuNet orders landmarks: right eye, left eye, nose tip, right and left mouth corner.
    points = [Point(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
    right_eye, left_eye, nose, right_mouth, left_mouth = points
    return FaceBox(
        x, y, w, h, float(row[_SCORE]), right_eye, left_eye, nose, right_mouth, left_mouth
    )


class YuNetDetector:
    """Verified YuNet network (tech.md §5.2, §7).

    The OpenCV detector is not thread-safe and keeps the input size as state, so calls
    are serialized with a lock on the instance.
    """

    def __init__(self, model_path: Path, score_threshold: float) -> None:
        verify_model(model_path)
        self._threshold = score_threshold
        self._detector = cv2.FaceDetectorYN.create(
            str(model_path), "", YUNET_INPUT_SIZE, score_threshold
        )
        self._lock = threading.Lock()

    def is_ready(self) -> bool:
        """True once the network has been constructed."""
        return self._detector is not None

    def detect(self, image: RgbImage) -> list[FaceBox]:
        """Faces on an RGB image, best score first."""
        height, width = image.shape[:2]
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        with self._lock:
            self._detector.setInputSize((width, height))
            _, rows = self._detector.detect(bgr)
        if rows is None:
            return []
        faces = [_face_from_row(row) for row in rows if float(row[_SCORE]) >= self._threshold]
        return sorted(faces, key=lambda f: f.score, reverse=True)


class FakeDetector:
    """Returns the faces given to it; lets analyzer tests run without the ONNX model."""

    def __init__(self, faces: Sequence[FaceBox] = ()) -> None:
        self._faces = tuple(faces)

    def detect(self, image: RgbImage) -> list[FaceBox]:
        """The configured faces, whatever the image."""
        del image
        return list(self._faces)
