"""Mapping of domain errors to HTTP responses; the only place that knows status codes."""

import logging
from collections.abc import Mapping
from types import MappingProxyType

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from real2block.api.schemas import ErrorBody, ErrorResponse
from real2block.domain.errors import ErrorCode, Real2blockError
from real2block.log import request_id_var

logger = logging.getLogger(__name__)

STATUS: Mapping[ErrorCode, int] = MappingProxyType(
    {
        "CONSENT_REQUIRED": 400,
        "FILE_TOO_LARGE": 413,
        "UNSUPPORTED_FORMAT": 415,
        "IMAGE_TOO_SMALL": 422,
        "IMAGE_TOO_LARGE": 422,
        "NO_FACE": 422,
        "INVALID_SPEC": 422,
        "INVALID_SKIN": 422,
        "INVALID_OPTIONS": 422,
        "RATE_LIMITED": 429,
        "INTERNAL": 500,
    }
)

MESSAGES: Mapping[ErrorCode, str] = MappingProxyType(
    {
        "CONSENT_REQUIRED": "Consent to photo processing is required",
        "FILE_TOO_LARGE": "File is too large",
        "UNSUPPORTED_FORMAT": "Unsupported file format",
        "IMAGE_TOO_SMALL": "Image is too small",
        "IMAGE_TOO_LARGE": "Image is too large",
        "NO_FACE": "No face found on the photo",
        "INVALID_SPEC": "Invalid skin spec",
        "INVALID_SKIN": "Invalid skin image",
        "INVALID_OPTIONS": "Invalid options",
        "RATE_LIMITED": "Too many requests, try again later",
        "INTERNAL": "Internal error",
    }
)

# Validation errors are attributed to the request field that failed; a JSON
# body that is neither of these is a SkinSpec.
FIELD_CODES: Mapping[str, ErrorCode] = MappingProxyType(
    {"skin": "INVALID_SKIN", "options": "INVALID_OPTIONS", "photo": "UNSUPPORTED_FORMAT"}
)
DEFAULT_VALIDATION_CODE: ErrorCode = "INVALID_SPEC"
JSON_CONTENT_TYPE = "application/json"

ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    status: {"model": ErrorResponse} for status in sorted(set(STATUS.values()))
}


def error_response(code: ErrorCode) -> JSONResponse:
    """Uniform error envelope for a code; never includes internal details."""
    body = ErrorResponse(
        error=ErrorBody(code=code, message=MESSAGES[code], request_id=request_id_var.get())
    )
    return JSONResponse(body.model_dump(), status_code=STATUS[code])


def _validation_code(request: Request, exc: RequestValidationError) -> ErrorCode:
    # A JSON body is always a SkinSpec: its keys, such as palette.skin, must not
    # read as the `skin` upload of the form routes.
    if request.headers.get("content-type", "").startswith(JSON_CONTENT_TYPE):
        return DEFAULT_VALIDATION_CODE
    for err in exc.errors():
        loc = err.get("loc", ())
        field = loc[1] if len(loc) > 1 else None
        if isinstance(field, str) and field in FIELD_CODES:
            return FIELD_CODES[field]
    return DEFAULT_VALIDATION_CODE


async def _domain_handler(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, Real2blockError):
        raise exc
    level = logging.ERROR if exc.code == "INTERNAL" else logging.INFO
    logger.log(level, "domain error: %s", exc.detail, extra={"codes": [exc.code]})
    return error_response(exc.code)


async def _validation_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    code = _validation_code(request, exc)
    logger.info("validation failed", extra={"codes": [code]})
    return error_response(code)


def install_error_handlers(app: FastAPI) -> None:
    """Register the single error mapping for the app."""
    app.add_exception_handler(Real2blockError, _domain_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
