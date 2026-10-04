"""Domain error and warning codes (closed sets, tech.md §5.2 and §5.4)."""

from typing import Literal

ErrorCode = Literal[
    "CONSENT_REQUIRED",
    "FILE_TOO_LARGE",
    "UNSUPPORTED_FORMAT",
    "IMAGE_TOO_SMALL",
    "IMAGE_TOO_LARGE",
    "NO_FACE",
    "INVALID_SPEC",
    "INVALID_SKIN",
    "INVALID_OPTIONS",
    "RATE_LIMITED",
    "INTERNAL",
]

WarningCode = Literal[
    "MULTIPLE_FACES",
    "FACE_TOO_SMALL",
    "LOW_LIGHT",
    "HAIR_NOT_DETECTED",
    "TORSO_NOT_VISIBLE",
    "PALETTE_REDUCED",
    "TRANSPARENT_BASE_PIXELS",
]


class BlockfoldError(Exception):
    """Base domain error carrying a public error code."""

    code: ErrorCode = "INTERNAL"

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self.code)
        self.detail = detail


class FileTooLargeError(BlockfoldError):
    """Request body exceeds the route limit."""

    code = "FILE_TOO_LARGE"


class UnsupportedFormatError(BlockfoldError):
    """File is not one of the accepted image formats."""

    code = "UNSUPPORTED_FORMAT"


class InvalidSkinError(BlockfoldError):
    """Skin image is malformed or has wrong dimensions."""

    code = "INVALID_SKIN"


class InvalidOptionsError(BlockfoldError):
    """Papercraft options failed validation."""

    code = "INVALID_OPTIONS"


class RateLimitedError(BlockfoldError):
    """Client exceeded the route rate limit."""

    code = "RATE_LIMITED"


class InternalError(BlockfoldError):
    """Unexpected failure, including heavy-call timeouts."""

    code = "INTERNAL"
