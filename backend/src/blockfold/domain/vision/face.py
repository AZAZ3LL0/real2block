"""Face detector model loading and integrity check (tech.md §8.2 item 7)."""

import hashlib
from pathlib import Path

import cv2

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


class YuNetModel:
    """Verified, loaded YuNet network; detection itself arrives with the vision slice."""

    def __init__(self, model_path: Path, score_threshold: float) -> None:
        verify_model(model_path)
        self._detector = cv2.FaceDetectorYN.create(
            str(model_path), "", YUNET_INPUT_SIZE, score_threshold
        )

    def is_ready(self) -> bool:
        """True once the network has been constructed."""
        return self._detector is not None
