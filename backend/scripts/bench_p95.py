"""Measure p95 latency of /analyze, /skin and /papercraft against a running stack (tech.md §7).

Usage: uv run python scripts/bench_p95.py [base_url] [--runs N]
Start the stack with docker/compose.bench.yml: it pins the API to 2 vCPU and lifts
the rate limits that would otherwise stop the run. Exits 1 if any target is missed.
"""

import argparse
import io
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
PHOTO = FIXTURES / "photos" / "frontal_white_tshirt.jpg"
SKIN = FIXTURES / "reference_skin.png"
API = "/api/v1"
PHOTO_12MP = (4000, 3000)
PHOTO_QUALITY = 90
WARMUP = 3
MAX_PDF_BYTES = 2 * 1024 * 1024
TIMEOUT_S = 30
# /skin keeps its fixed 300/hour limit (tech.md §8.2); the bench override cannot lift it.
SKIN_RATE_PER_HOUR = 300


@dataclass(frozen=True, slots=True)
class Target:
    """One measured call and its §7 budget."""

    name: str
    p95_ms: float
    runs: int


@dataclass(frozen=True, slots=True)
class Request:
    """A prepared HTTP request body."""

    path: str
    body: bytes
    content_type: str


def multipart(
    path: str, fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]
) -> Request:
    """Encode a multipart/form-data request."""
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        header = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
        parts.append(header.encode() + value.encode() + b"\r\n")
    for name, (filename, data, mime) in files.items():
        header = (
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="{name}"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'
        )
        parts.append(header.encode() + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return Request(path, b"".join(parts), f"multipart/form-data; boundary={boundary}")


def photo_12mp(fmt: str) -> bytes:
    """A fixture photo upscaled to 12 MP, the size §7 budgets for."""
    with Image.open(PHOTO) as img:
        big = img.convert("RGB").resize(PHOTO_12MP, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    big.save(buf, format=fmt, quality=PHOTO_QUALITY)
    return buf.getvalue()


def send(base: str, req: Request) -> tuple[float, bytes]:
    """POST the request; elapsed milliseconds and the response body."""
    http = urllib.request.Request(  # noqa: S310 - base URL is the operator's own stack
        base + req.path, data=req.body, headers={"Content-Type": req.content_type}
    )
    started = time.perf_counter()
    with urllib.request.urlopen(http, timeout=TIMEOUT_S) as response:  # noqa: S310
        body: bytes = response.read()
    return (time.perf_counter() - started) * 1000, body


def p95(samples: list[float]) -> float:
    """95th percentile, inclusive method so small samples stay within the data."""
    return statistics.quantiles(samples, n=20, method="inclusive")[18]


def measure(base: str, req: Request, runs: int) -> tuple[list[float], bytes]:
    """Latencies of `runs` sequential calls after a warmup, and the last body."""
    body = b""
    for _ in range(WARMUP):
        send(base, req)
    samples: list[float] = []
    for _ in range(runs):
        elapsed, body = send(base, req)
        samples.append(elapsed)
    return samples, body


def analyze_request(fmt: str, mime: str) -> Request:
    """/analyze with a 12 MP photo in the given format."""
    photo = {"photo": ("photo", photo_12mp(fmt), mime)}
    return multipart(f"{API}/analyze", {"consent": "true"}, photo)


def papercraft_request(mode: str) -> Request:
    """/papercraft on A4 at the default 5 mm cell, the setting §7 budgets the size for."""
    return multipart(
        f"{API}/papercraft",
        {"options": json.dumps({"paper": "A4", "pixel_mm": 5, "mode": mode})},
        {"skin": ("skin.png", SKIN.read_bytes(), "image/png")},
    )


def build_requests(base: str) -> tuple[Request, ...]:
    """Requests as the web client sends them, in the order of `targets`."""
    analyze = analyze_request("JPEG", "image/jpeg")
    # JPEG decodes at a reduced scale; WebP has no such shortcut and is the worst case.
    analyze_webp = analyze_request("WEBP", "image/webp")
    # /skin gets the spec the analyzer produced, as in the real flow.
    _, answer = send(base, analyze)
    spec = json.dumps(json.loads(answer)["spec"]).encode()
    skin = Request(f"{API}/skin", spec, "application/json")
    return analyze, analyze_webp, skin, papercraft_request("color"), papercraft_request("numbered")


def run(base: str, runs: int) -> bool:
    """Measure every route, print a table and report whether all budgets hold."""
    requests = build_requests(base)
    targets = (
        Target("analyze jpeg", 1500, runs),
        Target("analyze webp", 1500, runs),
        Target("skin", 50, runs),
        Target("pdf color", 1000, runs),
        Target("pdf numbered", 1000, runs),
    )
    ok = True
    print(f"{'route':<14}{'runs':>6}{'p50 ms':>10}{'p95 ms':>10}{'budget':>10}")
    for target, req in zip(targets, requests, strict=True):
        samples, body = measure(base, req, target.runs)
        value = p95(samples)
        ok &= value <= target.p95_ms
        median = statistics.median(samples)
        print(
            f"{target.name:<14}{target.runs:>6}{median:>10.0f}{value:>10.0f}{target.p95_ms:>10.0f}"
        )
        if req.path.endswith("/papercraft"):
            ok &= len(body) <= MAX_PDF_BYTES
            print(f"  pdf size {len(body) / 1024:.0f} KiB, budget {MAX_PDF_BYTES // 1024} KiB")
    return ok


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base_url", nargs="?", default="http://localhost:8080")
    parser.add_argument("--runs", type=int, default=40)
    args = parser.parse_args()
    if args.runs + WARMUP > SKIN_RATE_PER_HOUR:
        parser.error(f"--runs must leave room in the /skin limit of {SKIN_RATE_PER_HOUR}/hour")
    try:
        ok = run(args.base_url.rstrip("/"), args.runs)
    except urllib.error.HTTPError as exc:
        hint = " (rate limited: restart the api container)" if exc.code == 429 else ""
        sys.exit(f"FAIL: {exc.url} answered {exc.code}{hint}")
    print("OK" if ok else "FAIL: a §7 budget is exceeded")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
