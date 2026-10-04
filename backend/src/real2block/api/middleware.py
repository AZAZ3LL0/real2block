"""ASGI middleware chain: security headers, request context, rate limit, body limit."""

import hashlib
import logging
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from real2block.api.errors import error_response
from real2block.domain.errors import ErrorCode
from real2block.log import request_id_var

logger = logging.getLogger("real2block.access")

Clock = Callable[[], float]

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' blob: data:; object-src 'none'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
HSTS_VALUE = "max-age=31536000; includeSubDomains"
SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"content-security-policy", CONTENT_SECURITY_POLICY.encode()),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
)
REQUEST_ID_HEADER = b"x-request-id"
SECONDS_PER_HOUR = 3600.0
PRUNE_EVERY = 1024


async def _send_error(scope: Scope, receive: Receive, send: Send, code: ErrorCode) -> None:
    await error_response(code)(scope, receive, send)


class SecurityHeadersMiddleware:
    """Adds security headers to every HTTP response, HSTS only in prod."""

    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        self.app = app
        extra = ((b"strict-transport-security", HSTS_VALUE.encode()),) if hsts else ()
        self.headers = SECURITY_HEADERS + extra

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + list(self.headers)
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestContextMiddleware:
    """Assigns a request id, writes the access log and turns crashes into INTERNAL."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status = 500
        response_started = False

        async def send_tracked(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (REQUEST_ID_HEADER, request_id.encode()),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_tracked)
        except Exception:
            logger.exception("unhandled error", extra={"codes": ["INTERNAL"]})
            if response_started:
                raise
            await _send_error(scope, receive, send_tracked, "INTERNAL")
        finally:
            logger.info(
                "request",
                extra={
                    "route": scope.get("path", ""),
                    "method": scope.get("method", ""),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "size": _content_length(scope),
                },
            )
            request_id_var.reset(token)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


@dataclass(slots=True)
class _Bucket:
    tokens: float
    updated: float


class TokenBucket:
    """In-memory token buckets per key; refill is continuous over an hour."""

    def __init__(self, per_hour: int, clock: Clock = time.monotonic) -> None:
        self._capacity = float(per_hour)
        self._rate = per_hour / SECONDS_PER_HOUR
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._calls = 0

    def allow(self, key: str) -> bool:
        """Take one token for the key if available."""
        now = self._clock()
        self._calls += 1
        if self._calls % PRUNE_EVERY == 0:
            self._prune(now)
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = self._buckets[key] = _Bucket(self._capacity, now)
        bucket.tokens = min(self._capacity, bucket.tokens + (now - bucket.updated) * self._rate)
        bucket.updated = now
        if bucket.tokens < 1.0:
            return False
        bucket.tokens -= 1.0
        return True

    def _prune(self, now: float) -> None:
        # Buckets idle for an hour are full again and equivalent to absent ones.
        stale = [k for k, b in self._buckets.items() if now - b.updated >= SECONDS_PER_HOUR]
        for key in stale:
            del self._buckets[key]


class RateLimitMiddleware:
    """Per-route rate limit keyed by a salted hash of the client address."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limits: Mapping[str, int],
        salt: bytes,
        clock: Clock = time.monotonic,
    ) -> None:
        self.app = app
        self.salt = salt
        self.buckets = {path: TokenBucket(n, clock) for path, n in limits.items()}

    def _key(self, scope: Scope) -> str:
        client = scope.get("client")
        host = client[0] if client else "unknown"
        return hashlib.sha256(self.salt + host.encode()).hexdigest()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        bucket = self.buckets.get(scope.get("path", "")) if scope["type"] == "http" else None
        limited = bucket is not None and scope.get("method") != "OPTIONS"
        if limited and bucket is not None and not bucket.allow(self._key(scope)):
            await _send_error(scope, receive, send, "RATE_LIMITED")
            return
        await self.app(scope, receive, send)


class BodyLimitMiddleware:
    """Rejects bodies over the route limit before parsing, by header and by stream."""

    def __init__(self, app: ASGIApp, *, limits: Mapping[str, int], default: int) -> None:
        self.app = app
        self.limits = limits
        self.default = default

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = self.limits.get(scope.get("path", ""), self.default)
        declared = _content_length(scope)
        if declared is not None and declared > limit:
            await _send_error(scope, receive, send, "FILE_TOO_LARGE")
            return
        # Buffer the bounded body up front: an error raised mid-parse would be
        # swallowed by FastAPI's form parsing and reported as a generic 400.
        body = await _read_body(receive, limit)
        if body is None:
            await _send_error(scope, receive, send, "FILE_TOO_LARGE")
            return
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay, send)


async def _read_body(receive: Receive, limit: int) -> bytes | None:
    """Whole request body, or None once it exceeds the limit."""
    chunks: list[bytes] = []
    size = 0
    while True:
        message = await receive()
        if message["type"] != "http.request":
            return b"".join(chunks)
        chunk = message.get("body", b"")
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
        if not message.get("more_body", False):
            return b"".join(chunks)
