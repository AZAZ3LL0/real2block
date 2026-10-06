"""JSON logging with the current request id in every record."""

import json
import logging
from collections.abc import Iterable
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
# Warning and error codes of the current request, gathered for its access log line.
# The middleware sets a fresh list; the list itself is shared with thread-pool copies.
request_codes_var: ContextVar[list[str] | None] = ContextVar("request_codes", default=None)

# Fields added via `extra=`; anything else passed there is dropped so that
# file names, EXIF or client addresses can never reach the log by accident.
ALLOWED_EXTRA = ("route", "method", "status", "duration_ms", "size", "codes")


class JsonFormatter(logging.Formatter):
    """One JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize the record with the request id and whitelisted extras."""
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key in ALLOWED_EXTRA:
            if key in record.__dict__:
                payload[key] = record.__dict__[key]
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def note_codes(codes: Iterable[str]) -> None:
    """Add warning or error codes to the access log line of the current request."""
    collected = request_codes_var.get()
    if collected is not None:
        collected.extend(codes)


def configure_logging(level: str) -> None:
    """Route all logs through the JSON formatter; uvicorn access logs carry IPs, so mute them."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers[:] = []
        logging.getLogger(name).propagate = True
    logging.getLogger("uvicorn.access").disabled = True
