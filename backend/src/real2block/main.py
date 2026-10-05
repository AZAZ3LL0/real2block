"""Application factory: config, then dependencies, then the FastAPI app."""

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from fastapi import FastAPI
from starlette.formparsers import MultiPartParser
from starlette.middleware.cors import CORSMiddleware

from real2block.api.deps import Container, HeavyRunner, ReadinessProbe
from real2block.api.errors import install_error_handlers
from real2block.api.middleware import (
    BodyLimitMiddleware,
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from real2block.api.routes import API_PREFIX, WARNINGS_HEADER, router
from real2block.api.schemas import PapercraftOptions
from real2block.config import Settings
from real2block.domain.papercraft.document import PapercraftService
from real2block.domain.papercraft.pdf import PdfRenderer
from real2block.domain.stylize.base import Stylizer, StylizerId
from real2block.domain.stylize.downsample import DownsampleStylizer
from real2block.domain.stylize.grids import TEMPLATES_DIR, load_template_dir
from real2block.domain.stylize.template import TemplateStylizer
from real2block.domain.vision.analyzer import PhotoAnalyzer
from real2block.domain.vision.face import FaceDetector, YuNetDetector
from real2block.domain.vision.loader import configure_pillow
from real2block.log import configure_logging

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


class Real2blockApp(FastAPI):
    """FastAPI app whose OpenAPI also lists models sent inside multipart fields."""

    def openapi(self) -> dict[str, Any]:
        """Schema with PapercraftOptions, which travels as a JSON form string."""
        if self.openapi_schema is None:
            schema = super().openapi()
            components = schema.setdefault("components", {}).setdefault("schemas", {})
            components["PapercraftOptions"] = PapercraftOptions.model_json_schema()
        return super().openapi()


def _stylizers(template: TemplateStylizer) -> Mapping[StylizerId, Stylizer]:
    """Registry looked up by `spec.stylizer`; handlers never branch on it (tech.md §5.3)."""
    return MappingProxyType({"template": template, "downsample": DownsampleStylizer(template)})


def _face_parts(
    settings: Settings, face_model: ReadinessProbe | None, detector: FaceDetector | None
) -> tuple[ReadinessProbe, FaceDetector]:
    """One YuNet instance serves readiness and detection unless tests replace both."""
    if face_model is not None and detector is not None:
        return face_model, detector
    yunet = YuNetDetector(settings.face_model_path, settings.face_score_threshold)
    return face_model or yunet, detector or yunet


def app_factory(
    settings: Settings | None = None,
    face_model: ReadinessProbe | None = None,
    detector: FaceDetector | None = None,
    templates_dir: Path = TEMPLATES_DIR,
) -> FastAPI:
    """Build the app; fails fast on invalid config, templates or a tampered face model."""
    settings = settings or Settings()
    _configure_process(settings)
    templates = load_template_dir(templates_dir)
    face_model, detector = _face_parts(settings, face_model, detector)
    container = Container(
        face_model=face_model,
        papercraft=PapercraftService(PdfRenderer()),
        heavy=HeavyRunner(),
        stylizers=_stylizers(TemplateStylizer.from_templates(templates)),
        analyzer=PhotoAnalyzer(detector),
    )
    app = Real2blockApp(title="real2block API", version="1", docs_url=None, redoc_url=None)
    app.state.container = container
    install_error_handlers(app)
    app.include_router(router)
    _add_middleware(app, settings)
    return app
