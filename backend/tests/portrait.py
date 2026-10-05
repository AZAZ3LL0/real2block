"""Synthetic portraits: flat rectangles of known colors and the matching FaceBox."""

from dataclasses import dataclass

import numpy as np

from real2block.domain.color import Rgb
from real2block.domain.vision.face import FaceBox, Point
from real2block.domain.vision.loader import RgbImage

BACKGROUND = Rgb(0xD8, 0xE4, 0xF0)
SKIN = Rgb(0xC6, 0x8E, 0x6A)
HAIR = Rgb(0x3A, 0x24, 0x16)
EYE_WHITE = Rgb(0xF4, 0xF4, 0xF0)
IRIS = Rgb(0x2A, 0x4A, 0x7A)
MOUTH = Rgb(0xA0, 0x40, 0x40)
SHIRT = Rgb(0x2E, 0x8B, 0x57)


@dataclass(frozen=True, slots=True)
class Portrait:
    """Scene description; every color is drawn as a solid area."""

    width: int = 800
    height: int = 1000
    face: tuple[int, int, int, int] = (300, 250, 200, 240)
    background: Rgb = BACKGROUND
    skin: Rgb = SKIN
    hair: Rgb | None = HAIR
    long_hair: bool = False
    hair_margin: float = 0.2
    """How far hair reaches past the face sides, in face widths."""
    hair_top: float = 0.4
    """How far hair reaches above the face, in face heights."""
    eye_white: Rgb = EYE_WHITE
    iris: Rgb = IRIS
    mouth: Rgb = MOUTH
    shirt: Rgb = SHIRT

    def box(self) -> FaceBox:
        """FaceBox a perfect detector would report for this scene."""
        x, y, w, h = self.face
        return FaceBox(
            x, y, w, h, 0.95,
            right_eye=Point(x + 0.3 * w, y + 0.4 * h),
            left_eye=Point(x + 0.7 * w, y + 0.4 * h),
            nose=Point(x + 0.5 * w, y + 0.6 * h),
            right_mouth=Point(x + 0.35 * w, y + 0.8 * h),
            left_mouth=Point(x + 0.65 * w, y + 0.8 * h),
        )  # fmt: skip

    def render(self) -> RgbImage:
        """Draw the scene back to front."""
        img = np.empty((self.height, self.width, 3), dtype=np.uint8)
        img[:] = _c(self.background)
        x, y, w, h = self.face
        neck_bottom = y + round(1.15 * h)
        img[neck_bottom:, max(0, x - w // 2) : x + w + w // 2] = _c(self.shirt)
        if self.hair is not None:
            hair_bottom = y + round((1.6 if self.long_hair else 0.6) * h)
            top, margin = y - round(self.hair_top * h), round(self.hair_margin * w)
            img[max(0, top) : hair_bottom, max(0, x - margin) : x + w + margin] = _c(self.hair)
        img[y : y + h, x : x + w] = _c(self.skin)
        img[y + h : neck_bottom, x + w // 3 : x + 2 * w // 3] = _c(self.skin)
        box = self.box()
        for eye in (box.right_eye, box.left_eye):
            _square(img, eye, 0.08 * w, self.eye_white)
            _square(img, eye, 0.04 * w, self.iris)
        mouth_y = round(box.right_mouth.y)
        half = round(0.03 * w)
        img[mouth_y - half : mouth_y + half, round(box.right_mouth.x) : round(box.left_mouth.x)] = (
            _c(self.mouth)
        )
        return img


def _c(color: Rgb) -> tuple[int, int, int]:
    return color.r, color.g, color.b


def _square(img: RgbImage, center: Point, side: float, color: Rgb) -> None:
    half = side / 2
    y0, y1 = round(center.y - half), round(center.y + half)
    x0, x1 = round(center.x - half), round(center.x + half)
    img[y0:y1, x0:x1] = _c(color)
