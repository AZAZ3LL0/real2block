"""Pydantic request/response schemas; the API contract (tech.md §5.4)."""

from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from real2block.domain.color import Rgb
from real2block.domain.errors import ErrorCode, WarningCode
from real2block.domain.skin.geometry import Model, part_box
from real2block.domain.stylize import base
from real2block.domain.stylize.base import HairStyle, StylizerId

HexColor = Annotated[
    str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$"), AfterValidator(str.upper)
]
"""`#RRGGBB`, normalized to upper case."""

_HEAD = part_box("head")
FACE_FRONT_SHAPE = (_HEAD.h, _HEAD.w)
"""Rows and columns of `face_front`: the size of the head front face."""


class StrictModel(BaseModel):
    """Base for all schemas: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


class ErrorBody(StrictModel):
    """Error details."""

    code: ErrorCode
    message: str
    request_id: str


class ErrorResponse(StrictModel):
    """Uniform error envelope."""

    error: ErrorBody


class HealthResponse(StrictModel):
    """Liveness and model readiness."""

    status: Literal["ok"]


class NormalizeResponse(StrictModel):
    """Imported skin in 64x64 form."""

    skin_png_base64: str
    model: Literal["classic", "slim"]
    warnings: list[WarningCode]


class PapercraftOptions(StrictModel):
    """Papercraft PDF options."""

    model: Literal["classic", "slim", "auto"] = "auto"
    paper: Literal["A4", "Letter"] = "A4"
    pixel_mm: float = Field(5.0, ge=3.0, le=8.0)
    mode: Literal["color", "numbered"] = "color"
    flatten_overlay: bool = True
    grid_lines: bool = True
    lang: Literal["ru", "en"] = "ru"


class Palette(StrictModel):
    """Base color of every palette role."""

    skin: HexColor
    hair: HexColor
    eye_white: HexColor
    iris: HexColor
    mouth: HexColor
    shirt: HexColor
    pants: HexColor
    shoes: HexColor


class SkinSpec(StrictModel):
    """Everything needed to regenerate a skin; the client keeps it between calls."""

    spec_version: Literal[1] = 1
    model: Model = "classic"
    stylizer: StylizerId = "template"
    hair_style: HairStyle = "short"
    palette: Palette
    face_front: list[list[HexColor]] | None = None

    @model_validator(mode="after")
    def _check_face_front(self) -> Self:
        if self.stylizer != "downsample":
            return self
        rows, cols = FACE_FRONT_SHAPE
        face = self.face_front
        if face is None or len(face) != rows or any(len(row) != cols for row in face):
            raise ValueError(f"face_front must be {rows}x{cols} for the downsample stylizer")
        return self

    @classmethod
    def from_domain(cls, spec: base.SkinSpec) -> "SkinSpec":
        """API spec with colors formatted as hex."""
        face = spec.face_front
        return cls(
            model=spec.model,
            stylizer=spec.stylizer,
            hair_style=spec.hair_style,
            palette=Palette(
                **{role: getattr(spec.palette, role).to_hex() for role in Palette.model_fields}
            ),
            face_front=[[c.to_hex() for c in row] for row in face] if face else None,
        )

    def to_domain(self) -> base.SkinSpec:
        """Domain spec with colors parsed into `Rgb`."""
        palette = base.Palette(
            **{role: Rgb.from_hex(value) for role, value in self.palette.model_dump().items()}
        )
        face = self.face_front
        return base.SkinSpec(
            model=self.model,
            stylizer=self.stylizer,
            hair_style=self.hair_style,
            palette=palette,
            face_front=tuple(tuple(map(Rgb.from_hex, row)) for row in face) if face else None,
        )


class AnalyzeResponse(StrictModel):
    """Spec guessed from a photo and warnings for the user."""

    spec: SkinSpec
    warnings: list[WarningCode]
