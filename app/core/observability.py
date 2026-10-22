"""Request correlation, safe structured access logs and baseline security headers."""
import json
import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from starlette.responses import Response

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_logger = logging.getLogger("oosys.request")


def correlation_id(value: str | None) -> str:
    """Accept only bounded printable IDs; otherwise generate an opaque UUID."""
    if value and _REQUEST_ID.fullmatch(value):
        return value
    return str(uuid.uuid4())


def install_observability(application: FastAPI) -> None:
    """Install middleware that never records request bodies, query strings or secrets."""

    @application.middleware("http")
    async def request_observability(request: Request, call_next) -> Response:
        request_id = correlation_id(request.headers.get("X-Request-ID"))
        request.state.correlation_id = request_id
        started = time.perf_counter()
        status_code = 500
        raised = False
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            return response
        except Exception:
            raised = True
            raise
        finally:
            entry = {
                "event": "http.request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500 if raised else status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            _logger.log(logging.ERROR if raised or status_code >= 500 else logging.INFO,
                        json.dumps(entry, separators=(",", ":")))
