"""HTTP contract from tech.md §5.4 and middleware rules from §8."""

import base64
import io
import json
import logging
import os
import tempfile
from collections.abc import Iterator
from dataclasses import replace

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from PIL import Image
from pypdf import PdfReader

from real2block.api.deps import Container
from real2block.config import Settings
from real2block.domain.papercraft.document import PapercraftResult, PrintOptions
from real2block.log import JsonFormatter
from real2block.main import app_factory
from tests.helpers import blank, png_bytes

API = "/api/v1"
A4_PT = (595.28, 841.89)
LETTER_PT = (612.0, 792.0)


def make_app(**overrides: object) -> FastAPI:
    return app_factory(Settings.model_validate({"app_env": "dev", **overrides}))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(make_app()) as test_client:
        yield test_client


def _upload(data: bytes, name: str = "skin.png") -> dict[str, tuple[str, bytes, str]]:
    return {"skin": (name, data, "image/png")}


def _papercraft(client: TestClient, data: bytes, **options: object) -> Response:
    return client.post(
        f"{API}/papercraft", files=_upload(data), data={"options": json.dumps(options)}
    )


def _error_code(response: Response) -> str:
    code: str = response.json()["error"]["code"]
    return code


def _pdf(response: Response) -> PdfReader:
    return PdfReader(io.BytesIO(response.content))


# healthz and middleware


def test_healthz(client: TestClient) -> None:
    response = client.get(f"{API}/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers_and_request_id(client: TestClient) -> None:
    response = client.get(f"{API}/healthz")
    assert len(response.headers["x-request-id"]) == 32
    assert "unsafe-inline" not in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert "camera=()" in response.headers["permissions-policy"]
    assert "strict-transport-security" not in response.headers


def test_hsts_only_in_prod() -> None:
    with TestClient(make_app(app_env="prod", ip_hash_salt="s" * 32)) as client:
        response = client.get(f"{API}/healthz")
    assert "max-age" in response.headers["strict-transport-security"]


def test_cors_only_for_dev_origin(client: TestClient) -> None:
    allowed = client.get(f"{API}/healthz", headers={"Origin": "http://localhost:5173"})
    denied = client.get(f"{API}/healthz", headers={"Origin": "https://evil.example"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers


def test_healthz_fails_when_model_not_ready() -> None:
    class NotReady:
        def is_ready(self) -> bool:
            return False

    with TestClient(app_factory(Settings(), face_model=NotReady())) as client:
        response = client.get(f"{API}/healthz")
    assert response.status_code == 500
    assert _error_code(response) == "INTERNAL"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_body_limit_returns_413(client: TestClient) -> None:
    response = client.post(f"{API}/skin/normalize", files=_upload(b"\0" * 70_000))
    assert response.status_code == 413
    assert _error_code(response) == "FILE_TOO_LARGE"


def test_rate_limit_returns_429(reference_png: bytes) -> None:
    with TestClient(make_app(rate_papercraft_per_hour=2)) as client:
        statuses = [_papercraft(client, reference_png).status_code for _ in range(3)]
    assert statuses == [200, 200, 429]


def test_unhandled_error_becomes_internal(reference_png: bytes) -> None:
    class Crashing:
        def build(self, skin_png: bytes, options: PrintOptions) -> PapercraftResult:
            raise RuntimeError("secret internals")

    app = make_app()
    container: Container = app.state.container
    app.state.container = replace(container, papercraft=Crashing())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = _papercraft(client, reference_png)
    assert response.status_code == 500
    assert _error_code(response) == "INTERNAL"
    assert "secret" not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"


# /skin/normalize


def test_normalize_returns_64x64_png(client: TestClient, reference_png: bytes) -> None:
    response = client.post(f"{API}/skin/normalize", files=_upload(reference_png))
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "classic"
    assert body["warnings"] == []
    with Image.open(io.BytesIO(base64.b64decode(body["skin_png_base64"]))) as img:
        assert (img.size, img.mode) == ((64, 64), "RGBA")


def test_normalize_converts_legacy(client: TestClient, reference_png: bytes) -> None:
    with Image.open(io.BytesIO(reference_png)) as img:
        legacy = np.asarray(img)[:32].copy()
    response = client.post(f"{API}/skin/normalize", files=_upload(png_bytes(legacy)))
    with Image.open(io.BytesIO(base64.b64decode(response.json()["skin_png_base64"]))) as img:
        assert img.size == (64, 64)


@pytest.mark.parametrize(
    ("data", "status", "code"),
    [
        (b"\xff\xd8\xff\xe0" + b"\0" * 100, 415, "UNSUPPORTED_FORMAT"),
        (png_bytes(blank(63, 64)), 422, "INVALID_SKIN"),
    ],
)
def test_normalize_errors(client: TestClient, data: bytes, status: int, code: str) -> None:
    response = client.post(f"{API}/skin/normalize", files=_upload(data))
    assert response.status_code == status
    assert _error_code(response) == code


def test_normalize_requires_file(client: TestClient) -> None:
    response = client.post(f"{API}/skin/normalize")
    assert response.status_code == 422
    assert _error_code(response) == "INVALID_SKIN"


# /papercraft


def test_papercraft_returns_full_document(client: TestClient, reference_png: bytes) -> None:
    response = _papercraft(client, reference_png)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    disposition = response.headers["content-disposition"]
    assert disposition == 'attachment; filename="real2block-figure.pdf"'
    assert response.content.startswith(b"%PDF")
    pdf = _pdf(response)
    # Cover, printing guide, two net pages, assembly, legend.
    assert len(pdf.pages) == 6
    box = pdf.pages[0].mediabox
    assert (float(box.width), float(box.height)) == pytest.approx(A4_PT, abs=0.1)
    text = "".join(page.extract_text() for page in pdf.pages)
    for code in ("H", "B", "RA", "LA", "RL", "LL"):
        for letter in "ABCDEFG":
            assert f"{code}-{letter}" in text


def test_papercraft_rejects_cells_too_big_for_paper(
    client: TestClient, reference_png: bytes
) -> None:
    response = _papercraft(client, reference_png, pixel_mm=8)
    assert response.status_code == 422
    assert _error_code(response) == "INVALID_OPTIONS"


def test_papercraft_letter(client: TestClient, reference_png: bytes) -> None:
    box = _pdf(_papercraft(client, reference_png, paper="Letter")).pages[0].mediabox
    assert (float(box.width), float(box.height)) == pytest.approx(LETTER_PT, abs=0.1)


def test_papercraft_is_deterministic(client: TestClient, reference_png: bytes) -> None:
    first = _papercraft(client, reference_png, lang="en").content
    assert first == _papercraft(client, reference_png, lang="en").content


def test_papercraft_warns_about_transparent_base(client: TestClient) -> None:
    response = _papercraft(client, png_bytes(blank()))
    assert response.status_code == 200
    assert response.headers["x-real2block-warnings"] == "TRANSPARENT_BASE_PIXELS"


def test_papercraft_numbered_reports_palette_reduced(
    client: TestClient, reference_png: bytes
) -> None:
    numbered = _papercraft(client, reference_png, mode="numbered")
    colored = _papercraft(client, reference_png, mode="color")
    assert numbered.headers["x-real2block-warnings"] == "PALETTE_REDUCED"
    assert "x-real2block-warnings" not in colored.headers


@pytest.mark.parametrize(
    "options",
    ["not json", '{"pixel_mm": 9}', '{"pixel_mm": 2.5}', '{"paper": "A3"}', '{"extra": 1}'],
)
def test_papercraft_invalid_options(client: TestClient, reference_png: bytes, options: str) -> None:
    response = client.post(
        f"{API}/papercraft", files=_upload(reference_png), data={"options": options}
    )
    assert response.status_code == 422
    assert _error_code(response) == "INVALID_OPTIONS"


def test_papercraft_missing_options(client: TestClient, reference_png: bytes) -> None:
    response = client.post(f"{API}/papercraft", files=_upload(reference_png))
    assert _error_code(response) == "INVALID_OPTIONS"


def test_papercraft_rejects_legacy_skin(client: TestClient) -> None:
    response = _papercraft(client, png_bytes(blank(64, 32)))
    assert response.status_code == 422
    assert _error_code(response) == "INVALID_SKIN"


# privacy (tech.md §8.1, §10.9)


def test_uploads_leave_no_files_and_no_log_traces(reference_png: bytes) -> None:
    upload_name = "john-doe-passport.png"
    client = TestClient(make_app())
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logging.getLogger().addHandler(handler)
    tmp = tempfile.gettempdir()
    before = set(os.listdir(tmp))
    try:
        client.post(f"{API}/skin/normalize", files=_upload(reference_png, upload_name))
        client.post(
            f"{API}/papercraft",
            files=_upload(reference_png, upload_name),
            data={"options": "{}"},
        )
    finally:
        logging.getLogger().removeHandler(handler)
    assert set(os.listdir(tmp)) == before
    logs = stream.getvalue()
    assert '"route": "/api/v1/papercraft"' in logs
    assert upload_name not in logs
    assert "testclient" not in logs
    assert base64.b64encode(reference_png[:24]).decode() not in logs


def test_openapi_publishes_papercraft_options() -> None:
    schemas = make_app().openapi()["components"]["schemas"]
    assert schemas["PapercraftOptions"]["properties"]["pixel_mm"]["maximum"] == 8.0
