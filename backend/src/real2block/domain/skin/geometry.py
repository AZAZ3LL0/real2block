"""Skin UV layout (tech.md §4.1): the only module that knows texture coordinates."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, get_args

PartId = Literal["head", "body", "right_arm", "left_arm", "right_leg", "left_leg"]
FaceId = Literal["top", "bottom", "right", "front", "left", "back"]
Model = Literal["classic", "slim"]
Layer = Literal["base", "overlay"]

PART_IDS: tuple[PartId, ...] = get_args(PartId)
FACE_IDS: tuple[FaceId, ...] = get_args(FaceId)
LAYERS: tuple[Layer, ...] = get_args(Layer)

SKIN_SIZE = 64
LEGACY_HEIGHT = 32


@dataclass(frozen=True, slots=True)
class BoxSpec:
    """Box size in skin pixels: width, height, depth."""

    w: int
    h: int
    d: int


@dataclass(frozen=True, slots=True)
class Rect:
    """Axis-aligned rectangle in texture pixels; (x, y) is the top-left corner."""

    x: int
    y: int
    w: int
    h: int

    def cells(self) -> list[tuple[int, int]]:
        """All (x, y) pixel coordinates inside the rectangle, row-major."""
        return [(self.x + i, self.y + j) for j in range(self.h) for i in range(self.w)]


@dataclass(frozen=True, slots=True)
class PartSpec:
    """Box size and UV origins of one body part."""

    box: BoxSpec
    base: tuple[int, int]
    overlay: tuple[int, int]

    def origin(self, layer: Layer) -> tuple[int, int]:
        """UV origin of the given layer."""
        return self.base if layer == "base" else self.overlay


def uv_rect(box: BoxSpec, origin: tuple[int, int], face: FaceId) -> Rect:
    """Texture rectangle of one box face; the single Minecraft UV formula."""
    u, v = origin
    w, h, d = box.w, box.h, box.d
    match face:
        case "top":
            return Rect(u + d, v, w, d)
        case "bottom":
            return Rect(u + d + w, v, w, d)
        case "right":
            return Rect(u, v + d, d, h)
        case "front":
            return Rect(u + d, v + d, w, h)
        case "left":
            return Rect(u + d + w, v + d, d, h)
        case "back":
            return Rect(u + 2 * d + w, v + d, w, h)


def _parts(arm_width: int) -> Mapping[PartId, PartSpec]:
    arm = BoxSpec(arm_width, 12, 4)
    limb = BoxSpec(4, 12, 4)
    return MappingProxyType(
        {
            "head": PartSpec(BoxSpec(8, 8, 8), (0, 0), (32, 0)),
            "body": PartSpec(BoxSpec(8, 12, 4), (16, 16), (16, 32)),
            "right_arm": PartSpec(arm, (40, 16), (40, 32)),
            "left_arm": PartSpec(arm, (32, 48), (48, 48)),
            "right_leg": PartSpec(limb, (0, 16), (0, 32)),
            "left_leg": PartSpec(limb, (16, 48), (0, 48)),
        }
    )


PARTS: Mapping[Model, Mapping[PartId, PartSpec]] = MappingProxyType(
    {"classic": _parts(4), "slim": _parts(3)}
)


def face_rect(part: PartId, face: FaceId, layer: Layer = "base", model: Model = "classic") -> Rect:
    """Texture rectangle of a face of a body part."""
    spec = PARTS[model][part]
    return uv_rect(spec.box, spec.origin(layer), face)


def part_box(part: PartId, model: Model = "classic") -> BoxSpec:
    """Box size of a body part."""
    return PARTS[model][part].box


LEGACY_MIRRORS: Mapping[PartId, PartId] = MappingProxyType(
    {"left_arm": "right_arm", "left_leg": "right_leg"}
)
"""Parts missing in 64x32 skins and the part they are mirrored from."""

SLIM_PROBE_PIXEL = (50, 16)
SLIM_PROBE_COLUMNS = range(54, 56)
SLIM_PROBE_ROWS = range(20, 32)
"""Pixels that are fully transparent on slim skins (tech.md §4.1)."""
