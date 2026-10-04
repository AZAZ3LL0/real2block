"""Pydantic request/response schemas; the API contract (tech.md §5.4)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from blockfold.domain.errors import ErrorCode, WarningCode


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
