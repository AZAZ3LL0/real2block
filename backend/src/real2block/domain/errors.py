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


class Real2blockError(Exception):
    """Base domain error carrying a public error code."""

    code: ErrorCode = "INTERNAL"

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self.code)
        self.detail = detail


class ConsentRequiredError(Real2blockError):
    """Photo sent without consent to its processing."""

    code = "CONSENT_REQUIRED"


class NoFaceError(Real2blockError):
    """No face at or above the score threshold on the photo."""

    code = "NO_FACE"


class FileTooLargeError(Real2blockError):
    """Request body exceeds the route limit."""

    code = "FILE_TOO_LARGE"


class UnsupportedFormatError(Real2blockError):
    """File is not one of the accepted image formats."""

    code = "UNSUPPORTED_FORMAT"


class ImageTooSmallError(Real2blockError):
    """Photo is below the minimum dimensions."""

    code = "IMAGE_TOO_SMALL"


class ImageTooLargeError(Real2blockError):
    """Photo exceeds the maximum dimensions or pixel count."""

    code = "IMAGE_TOO_LARGE"


class InvalidSkinError(Real2blockError):
    """Skin image is malformed or has wrong dimensions."""

    code = "INVALID_SKIN"


class InvalidOptionsError(Real2blockError):
    """Papercraft options failed validation."""

    code = "INVALID_OPTIONS"


class RateLimitedError(Real2blockError):
    """Client exceeded the route rate limit."""

    code = "RATE_LIMITED"


class InternalError(Real2blockError):
    """Unexpected failure, including heavy-call timeouts."""

    code = "INTERNAL"
