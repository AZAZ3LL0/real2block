"""Color sampling by face regions, all in Lab (tech.md §5.2 step 3)."""

from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np
import numpy.typing as npt

from real2block.domain.color import delta_e, pixels_to_lab
from real2block.domain.vision.face import FaceBox, Point
from real2block.domain.vision.loader import RgbImage

Lab = npt.NDArray[np.float32]

CHEEK_PATCH = 0.12
"""Cheek patch side, in face widths."""
IRIS_PATCH = 0.06
"""Patch side around each eye point, in face widths."""
IRIS_CLUSTERS = 2
MOUTH_PATCH_HEIGHT = 0.05
"""Height of the patch between the mouth corners, in face widths."""
HAIR_TOP_HEIGHT = 0.35
"""Strip above the face, in face heights."""
HAIR_TOP_WIDTH = 1.2
"""Strip above the face, in face widths, centered on the face."""
HAIR_SIDE_WIDTH = 0.15
"""Strips on both sides of the face, in face widths."""
HAIR_SIDE_HEIGHT = 0.6
"""Side strip height, in face heights."""
HAIR_CLUSTERS = 3
CORNER_PATCH = 0.05
"""Background corner patch side, as a share of the frame side."""
SHIRT_TOP = 1.3
SHIRT_BOTTOM = 2.3
"""Shirt box top and bottom below the face top, in face heights."""
SHIRT_WIDTH = 1.6
"""Shirt box width, in face widths, centered on the face."""
SHIRT_MIN_VISIBLE = 0.3
"""Below this share of the shirt box inside the frame the torso counts as not visible."""
SHIRT_CLUSTERS = 3
SAME_COLOR_DELTA_E = 15.0
"""Colors closer than this count as the same: hair or cloth must differ from skin by more."""
SAMPLING_SEED = 4242
_KMEANS_CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.2)
_KMEANS_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class Rect:
    """Half-open pixel box [x0, x1) x [y0, y1)."""

    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def centered(cls, center: Point, width: float, height: float) -> "Rect":
        """Box of the given size around a point."""
        return cls(
            center.x - width / 2, center.y - height / 2, center.x + width / 2, center.y + height / 2
        )

    @property
    def area(self) -> float:
        """Area in square pixels; zero for an empty box."""
        return max(0.0, self.x1 - self.x0) * max(0.0, self.y1 - self.y0)

    def clip(self, width: int, height: int) -> "Rect":
        """The part of the box inside a frame."""
        return Rect(max(0.0, self.x0), max(0.0, self.y0), min(width, self.x1), min(height, self.y1))


@dataclass(frozen=True, slots=True)
class Cluster:
    """K-means cluster: Lab center and its pixel count."""

    center: Lab
    size: int


def _pixels(image: RgbImage, rects: Sequence[Rect]) -> Lab:
    """Lab pixels of all boxes clipped to the image; empty (0, 3) if nothing is inside."""
    height, width = image.shape[:2]
    parts = []
    for rect in rects:
        c = rect.clip(width, height)
        x0, y0, x1, y1 = round(c.x0), round(c.y0), round(c.x1), round(c.y1)
        if x1 > x0 and y1 > y0:
            parts.append(pixels_to_lab(image[y0:y1, x0:x1]))
    return np.concatenate(parts) if parts else np.empty((0, 3), dtype=np.float32)


def _median(lab: Lab) -> Lab | None:
    """Median color, or None when the region has no pixels inside the frame."""
    if len(lab) == 0:
        return None
    median: Lab = np.median(lab, axis=0).astype(np.float32)
    return median


def clusters(lab: Lab, k: int) -> list[Cluster]:
    """Deterministic k-means in Lab, largest cluster first."""
    k = min(k, len(lab))
    if k == 0:
        return []
    cv2.setRNGSeed(SAMPLING_SEED)
    initial = np.zeros((len(lab), 1), dtype=np.int32)
    _, labels, centers = cv2.kmeans(
        lab, k, initial, _KMEANS_CRITERIA, _KMEANS_ATTEMPTS, cv2.KMEANS_PP_CENTERS
    )
    counts = np.bincount(np.asarray(labels, dtype=np.int64).ravel(), minlength=k)
    found = [Cluster(centers[i].astype(np.float32), int(counts[i])) for i in range(k) if counts[i]]
    return sorted(found, key=lambda c: c.size, reverse=True)


def _midpoint(a: Point, b: Point) -> Point:
    return Point((a.x + b.x) / 2, (a.y + b.y) / 2)


def skin_lab(image: RgbImage, face: FaceBox) -> Lab | None:
    """Median of both cheeks, each centered between the eye and the mouth corner on its side.

    None when both cheeks are outside the frame.
    """
    side = CHEEK_PATCH * face.w
    cheeks = [
        Rect.centered(_midpoint(face.right_eye, face.right_mouth), side, side),
        Rect.centered(_midpoint(face.left_eye, face.left_mouth), side, side),
    ]
    return _median(_pixels(image, cheeks))


def iris_lab(image: RgbImage, face: FaceBox) -> Lab | None:
    """Darker of two clusters around both eye points; None when both eyes are off frame."""
    side = IRIS_PATCH * face.w
    eyes = [Rect.centered(face.right_eye, side, side), Rect.centered(face.left_eye, side, side)]
    found = clusters(_pixels(image, eyes), IRIS_CLUSTERS)
    return min(found, key=lambda c: float(c.center[0])).center if found else None


def mouth_lab(image: RgbImage, face: FaceBox) -> Lab | None:
    """Median of the strip between the mouth corners; None when the strip is off frame."""
    half = MOUTH_PATCH_HEIGHT * face.w / 2
    y = (face.right_mouth.y + face.left_mouth.y) / 2
    # On a turned head the detector may put the corners in either order.
    x0, x1 = sorted((face.right_mouth.x, face.left_mouth.x))
    strip = Rect(x0, y - half, x1, y + half)
    return _median(_pixels(image, [strip]))


def background_lab(image: RgbImage) -> Lab | None:
    """Median of the four corner patches."""
    height, width = image.shape[:2]
    pw, ph = CORNER_PATCH * width, CORNER_PATCH * height
    corners = [
        Rect(0, 0, pw, ph),
        Rect(width - pw, 0, width, ph),
        Rect(0, height - ph, pw, height),
        Rect(width - pw, height - ph, width, height),
    ]
    return _median(_pixels(image, corners))


def hair_rects(face: FaceBox, top: float) -> list[Rect]:
    """Strips beside the face starting at `top`, each `HAIR_SIDE_HEIGHT` face heights tall."""
    side_w, side_h = HAIR_SIDE_WIDTH * face.w, HAIR_SIDE_HEIGHT * face.h
    return [
        Rect(face.x - side_w, top, face.x, top + side_h),
        Rect(face.x + face.w, top, face.x + face.w + side_w, top + side_h),
    ]


def _largest_far_from(found: Sequence[Cluster], avoid: Sequence[Lab]) -> Lab | None:
    for cluster in found:
        if all(delta_e(cluster.center, other) >= SAME_COLOR_DELTA_E for other in avoid):
            return cluster.center
    return None


def hair_lab(image: RgbImage, face: FaceBox, skin: Lab, background: Lab | None) -> Lab | None:
    """Largest cluster above and beside the face that is neither skin nor background."""
    top_w, top_h = HAIR_TOP_WIDTH * face.w, HAIR_TOP_HEIGHT * face.h
    center_x = face.x + face.w / 2
    above = Rect(center_x - top_w / 2, face.y - top_h, center_x + top_w / 2, face.y)
    found = clusters(_pixels(image, [above, *hair_rects(face, face.y)]), HAIR_CLUSTERS)
    avoid = [skin] if background is None else [skin, background]
    return _largest_far_from(found, avoid)


def shirt_lab(image: RgbImage, face: FaceBox, skin: Lab) -> Lab | None:
    """Largest non-skin cluster below the face; None when the torso is mostly off frame."""
    height, width = image.shape[:2]
    center_x = face.x + face.w / 2
    half = SHIRT_WIDTH * face.w / 2
    box = Rect(
        center_x - half,
        face.y + SHIRT_TOP * face.h,
        center_x + half,
        face.y + SHIRT_BOTTOM * face.h,
    )
    if box.clip(width, height).area < SHIRT_MIN_VISIBLE * box.area:
        return None
    return _largest_far_from(clusters(_pixels(image, [box]), SHIRT_CLUSTERS), [skin])


def hair_share_below_mouth(image: RgbImage, face: FaceBox, hair: Lab) -> float:
    """Share of side-strip pixels below the mouth line that have the hair color."""
    mouth_y = max(face.right_mouth.y, face.left_mouth.y)
    lab = _pixels(image, hair_rects(face, mouth_y))
    if len(lab) == 0:
        return 0.0
    distances = np.linalg.norm(lab - hair, axis=1)
    return float(np.mean(distances < SAME_COLOR_DELTA_E))


def face_lightness(image: RgbImage, face: FaceBox) -> float:
    """Mean Lab lightness over the face box, 0..100."""
    lab = _pixels(image, [Rect(face.x, face.y, face.x + face.w, face.y + face.h)])
    return float(np.mean(lab[:, 0])) if len(lab) else 0.0
