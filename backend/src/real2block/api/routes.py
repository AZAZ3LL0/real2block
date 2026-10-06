"""HTTP routes under /api/v1 (tech.md §5.4)."""

import base64
from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import ValidationError

from real2block.api.deps import ContainerDep
from real2block.api.errors import ERROR_RESPONSES
from real2block.api.schemas import (
    AnalyzeResponse,
    HealthResponse,
    NormalizeResponse,
    PapercraftOptions,
    SkinSpec,
)
from real2block.domain.errors import ConsentRequiredError, InternalError, InvalidOptionsError
from real2block.domain.papercraft.document import PrintOptions
from real2block.domain.skin.io import normalize_skin

API_PREFIX = "/api/v1"
PDF_FILENAME = "real2block-figure.pdf"
WARNINGS_HEADER = "X-Real2block-Warnings"

router = APIRouter(prefix=API_PREFIX, responses=ERROR_RESPONSES)


@router.get("/healthz")
def healthz(container: ContainerDep) -> HealthResponse:
    """Liveness check that also requires the face model to be loaded."""
    if not container.face_model.is_ready():
        raise InternalError("face model not ready")
    return HealthResponse(status="ok")


CONSENT_VALUE = "true"


@router.post("/analyze")
async def analyze(
    container: ContainerDep,
    photo: Annotated[UploadFile, File()],
    consent: Annotated[str, Form()] = "",
) -> AnalyzeResponse:
    """Guess a skin spec from a photo; the photo is read into memory and dropped."""
    # Checked before reading the upload, so nothing is processed without consent.
    if consent != CONSENT_VALUE:
        raise ConsentRequiredError("consent is not 'true'")
    result = await container.heavy.run(container.analyzer.analyze, await photo.read())
    return AnalyzeResponse(spec=SkinSpec.from_domain(result.spec), warnings=list(result.warnings))


@router.post(
    "/skin",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "64x64 RGBA skin"}},
)
def render_skin(container: ContainerDep, spec: SkinSpec) -> Response:
    """Generate the skin PNG for a spec."""
    stylizer = container.stylizers.get(spec.stylizer)
    if stylizer is None:
        raise InternalError(f"stylizer {spec.stylizer} is not available")
    return Response(stylizer.render(spec.to_domain()).to_png(), media_type="image/png")


@router.post("/skin/normalize")
async def skin_normalize(skin: Annotated[UploadFile, File()]) -> NormalizeResponse:
    """Import a ready skin: 64x32 to 64x64 and model detection."""
    result = normalize_skin(await skin.read())
    return NormalizeResponse(
        skin_png_base64=base64.b64encode(result.skin.to_png()).decode("ascii"),
        model=result.model,
        warnings=list(result.warnings),
    )


def _parse_options(raw: str) -> PrintOptions:
    try:
        opts = PapercraftOptions.model_validate_json(raw)
    except ValidationError as exc:
        raise InvalidOptionsError("options failed validation") from exc
    return PrintOptions(**opts.model_dump())


@router.post(
    "/papercraft",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "Papercraft PDF"}},
)
async def papercraft(
    container: ContainerDep,
    skin: Annotated[UploadFile, File()],
    options: Annotated[str, Form(description="JSON-encoded PapercraftOptions")],
) -> Response:
    """Render the papercraft PDF for a 64x64 skin."""
    print_options = _parse_options(options)
    data = await skin.read()
    result = await container.heavy.run(container.papercraft.build, data, print_options)
    headers = {"Content-Disposition": f'attachment; filename="{PDF_FILENAME}"'}
    if result.warnings:
        headers[WARNINGS_HEADER] = ",".join(result.warnings)
    return Response(result.pdf, media_type="application/pdf", headers=headers)
