"""Photo to `SkinSpec` and warnings (tech.md §5.2)."""

from dataclasses import dataclass

import cv2

from real2block.domain.color import Rgb, from_lab, quantize
from real2block.domain.errors import NoFaceError, WarningCode
from real2block.domain.skin.geometry import part_box
from real2block.domain.stylize.base import HairStyle, Palette, SkinSpec
from real2block.domain.vision import sampling
from real2block.domain.vision.face import FaceBox, FaceDetector
from real2block.domain.vision.loader import RgbImage, load_photo

DEFAULT_HAIR = Rgb(0x4A, 0x32, 0x22)
DEFAULT_SHIRT = Rgb(0x3F, 0xA7, 0xA0)
DEFAULT_PANTS = Rgb(0x2E, 0x3A, 0x8C)
DEFAULT_SHOES = Rgb(0x3A, 0x3A, 0x3A)
DEFAULT_EYE_WHITE = Rgb(0xFF, 0xFF, 0xFF)
DEFAULT_IRIS = Rgb(0x3B, 0x2A, 0x1A)
DEFAULT_MOUTH = Rgb(0x9C, 0x5B, 0x4E)
"""Role defaults from tech.md §5.1; pants, shoes and eye whites are never sampled."""

MIN_FACE_WIDTH = 64
"""Narrower faces give FACE_TOO_SMALL (px, on the photo scaled to 1024)."""
LOW_LIGHT_L = 25.0
"""Mean face lightness below which LOW_LIGHT is reported."""
LONG_HAIR_SHARE = 0.4
"""Hair color share in the strips below the mouth that makes the style `long`."""
FACE_CROP_MARGIN = 0.15
"""Margin around the face for `face_front`, as a share of the face side."""
FACE_FRONT_COLORS = 6

_HEAD = part_box("head")
FACE_FRONT_SIZE = (_HEAD.w, _HEAD.h)
"""`face_front` is the head front face: 8x8."""


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    """Spec guessed from the photo plus what the user should double-check."""

    spec: SkinSpec
    warnings: tuple[WarningCode, ...]


def face_front(image: RgbImage, face: FaceBox) -> tuple[tuple[Rgb, ...], ...]:
    """Square face crop with a margin, area-averaged to 8x8 and reduced to 6 colors."""
    height, width = image.shape[:2]
    side = max(face.w, face.h) * (1 + 2 * FACE_CROP_MARGIN)
    cx, cy = face.x + face.w / 2, face.y + face.h / 2
    crop = sampling.Rect(cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2).clip(
        width, height
    )
    pixels = image[round(crop.y0) : round(crop.y1), round(crop.x0) : round(crop.x1)]
    small = cv2.resize(pixels, FACE_FRONT_SIZE, interpolation=cv2.INTER_AREA)
    colors = [Rgb(int(r), int(g), int(b)) for r, g, b in small.reshape(-1, 3)]
    mapping = quantize(colors, FACE_FRONT_COLORS)
    cols = FACE_FRONT_SIZE[0]
    return tuple(
        tuple(mapping[c] for c in colors[i : i + cols]) for i in range(0, len(colors), cols)
    )


def _or_default(lab: sampling.Lab | None, default: Rgb) -> Rgb:
    """Sampled color, or the tech.md §5.1 default for a role not found on the photo."""
    return default if lab is None else from_lab(lab)


class PhotoAnalyzer:
    """Pure in meaning: the photo lives only inside `analyze` (tech.md §8.1)."""

    def __init__(self, detector: FaceDetector) -> None:
        self._detector = detector

    def analyze(self, data: bytes) -> AnalyzeResult:
        """Decode, find the largest face and sample role colors."""
        image = load_photo(data)
        faces = self._detector.detect(image)
        if not faces:
            raise NoFaceError("no face above the threshold")
        face = max(faces, key=lambda f: f.area)
        warnings: list[WarningCode] = []
        if len(faces) > 1:
            warnings.append("MULTIPLE_FACES")
        if face.w < MIN_FACE_WIDTH:
            warnings.append("FACE_TOO_SMALL")
        if sampling.face_lightness(image, face) < LOW_LIGHT_L:
            warnings.append("LOW_LIGHT")
        palette, hair_style = self._palette(image, face, warnings)
        spec = SkinSpec(
            model="classic",
            stylizer="template",
            hair_style=hair_style,
            palette=palette,
            face_front=face_front(image, face),
        )
        return AnalyzeResult(spec, tuple(warnings))

    @staticmethod
    def _palette(
        image: RgbImage, face: FaceBox, warnings: list[WarningCode]
    ) -> tuple[Palette, HairStyle]:
        skin = sampling.skin_lab(image, face)
        if skin is None:
            # Skin has no default in tech.md §5.1: a face without visible cheeks is unusable.
            raise NoFaceError("both cheeks are outside the frame")
        background = sampling.background_lab(image)
        hair = sampling.hair_lab(image, face, skin, background)
        shirt = sampling.shirt_lab(image, face, skin)
        hair_style: HairStyle = "short"
        if hair is None:
            hair_style = "bald"
            warnings.append("HAIR_NOT_DETECTED")
        elif sampling.hair_share_below_mouth(image, face, hair) > LONG_HAIR_SHARE:
            hair_style = "long"
        if shirt is None:
            warnings.append("TORSO_NOT_VISIBLE")
        palette = Palette(
            skin=from_lab(skin),
            hair=_or_default(hair, DEFAULT_HAIR),
            eye_white=DEFAULT_EYE_WHITE,
            iris=_or_default(sampling.iris_lab(image, face), DEFAULT_IRIS),
            mouth=_or_default(sampling.mouth_lab(image, face), DEFAULT_MOUTH),
            shirt=_or_default(shirt, DEFAULT_SHIRT),
            pants=DEFAULT_PANTS,
            shoes=DEFAULT_SHOES,
        )
        return palette, hair_style
