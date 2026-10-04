"""Application factory: config, then dependencies, then the FastAPI app."""

from collections.abc import Mapping
from types import MappingProxyType

from fastapi import FastAPI
from starlette.formparsers import MultiPartParser
from starlette.middleware.cors import CORSMiddleware

from blockfold.api.deps import Container, HeavyRunner, ReadinessProbe
from blockfold.api.errors import install_error_handlers
from blockfold.api.middleware import (
    BodyLimitMiddleware,
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from blockfold.api.routes import API_PREFIX, WARNINGS_HEADER, router
from blockfold.config import Settings
from blockfold.domain.papercraft.document import PapercraftService
from blockfold.domain.papercraft.pdf import PdfRenderer
from blockfold.domain.vision.face import YuNetModel
from blockfold.domain.vision.loader import configure_pillow
from blockfold.log import configure_logging

SKIN_BODY_LIMIT = 16 * 1024
UPLOAD_BODY_LIMIT = 64 * 1024
LIGHT_RATE_PER_HOUR = 300


def _body_limits(settings: Settings) -> Mapping[str, int]:
    return MappingProxyType(
        {
            f"{API_PREFIX}/analyze": settings.max_photo_bytes,
            f"{API_PREFIX}/skin": SKIN_BODY_LIMIT,
            f"{API_PREFIX}/skin/normalize": UPLOAD_BODY_LIMIT,
            f"{API_PREFIX}/papercraft": UPLOAD_BODY_LIMIT,
        }
    )


def _rate_limits(settings: Settings) -> Mapping[str, int]:
    return MappingProxyType(
        {
            f"{API_PREFIX}/analyze": settings.rate_analyze_per_hour,
            f"{API_PREFIX}/papercraft": settings.rate_papercraft_per_hour,
            f"{API_PREFIX}/skin": LIGHT_RATE_PER_HOUR,
            f"{API_PREFIX}/skin/normalize": LIGHT_RATE_PER_HOUR,
        }
    )


def _configure_process(settings: Settings) -> None:
    configure_logging(settings.log_level)
    configure_pillow()
    # Keep every accepted upload in memory: photos must never be spooled to disk.
    MultiPartParser.spool_max_size = max(MultiPartParser.spool_max_size, settings.max_photo_bytes)


def _add_middleware(app: FastAPI, settings: Settings) -> None:
    # Added inner to outer: the last one wraps everything else.
    body_limits = _body_limits(settings)
    app.add_middleware(BodyLimitMiddleware, limits=body_limits, default=SKIN_BODY_LIMIT)
    app.add_middleware(
        RateLimitMiddleware, limits=_rate_limits(settings), salt=settings.salt_bytes()
    )
    if not settings.is_prod:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.cors_dev_origin],
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
            expose_headers=[WARNINGS_HEADER, "Content-Disposition"],
        )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_prod)


def app_factory(
    settings: Settings | None = None, face_model: ReadinessProbe | None = None
) -> FastAPI:
    """Build the app; fails fast on invalid config or a tampered face model."""
    settings = settings or Settings()
    _configure_process(settings)
    container = Container(
        face_model=face_model
        or YuNetModel(settings.face_model_path, settings.face_score_threshold),
        papercraft=PapercraftService(PdfRenderer()),
        heavy=HeavyRunner(),
    )
    app = FastAPI(title="Blockfold API", version="1", docs_url=None, redoc_url=None)
    app.state.container = container
    install_error_handlers(app)
    app.include_router(router)
    _add_middleware(app, settings)
    return app
