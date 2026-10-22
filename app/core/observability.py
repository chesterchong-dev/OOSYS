"""Request correlation, structured access logs, request metrics and baseline security headers."""
import hmac
import json
import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.core.metrics import RequestMetrics

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_logger = logging.getLogger("oosys.request")


def correlation_id(value: str | None) -> str:
    """Accept only bounded printable IDs; otherwise generate an opaque UUID."""
    if value and _REQUEST_ID.fullmatch(value):
        return value
    return str(uuid.uuid4())


def valid_metrics_token(supplied: str | None, configured: str | None) -> bool:
    """Compare the metrics scrape token without a timing-sensitive string comparison."""
    if not supplied or not configured:
        return False
    return hmac.compare_digest(supplied.encode(), configured.encode())


def install_observability(application: FastAPI) -> None:
    """Install safe access logging and bounded, process-local aggregate request metrics."""
    metrics = RequestMetrics()
    application.state.request_metrics = metrics

    @application.middleware("http")
    async def request_observability(request: Request, call_next) -> Response:
        request_id = correlation_id(request.headers.get("X-Request-ID"))
        request.state.correlation_id = request_id
        request.scope["headers"] = [
            (key, value) for key, value in request.scope["headers"]
            if key.lower() != b"x-request-id"
        ] + [(b"x-request-id", request_id.encode("ascii"))]
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
            duration = max(0.0, time.perf_counter() - started)
            final_status = 500 if raised else status_code
            metrics.observe(request.method, final_status, duration)
            entry = {
                "event": "http.request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": final_status,
                "duration_ms": round(duration * 1000, 2),
            }
            _logger.log(
                logging.ERROR if raised or final_status >= 500 else logging.INFO,
                json.dumps(entry, separators=(",", ":")),
            )
