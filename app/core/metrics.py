"""Process-local request metrics with bounded, low-cardinality labels."""
from collections import defaultdict
from threading import Lock


_KNOWN_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class RequestMetrics:
    """Store aggregate request counts and duration sums; never store paths or payloads."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counts: dict[tuple[str, int], int] = defaultdict(int)
        self._duration_sum: dict[tuple[str, int], float] = defaultdict(float)

    def observe(self, method: str, status_code: int, duration_seconds: float) -> None:
        """Record one completed request with bounded labels."""
        label_method = method if method in _KNOWN_METHODS else "OTHER"
        label_status = status_code if 100 <= status_code <= 599 else 500
        key = (label_method, label_status)
        with self._lock:
            self._counts[key] += 1
            self._duration_sum[key] += max(0.0, duration_seconds)

    def render_prometheus(self) -> str:
        """Render a minimal Prometheus text exposition without sensitive labels."""
        with self._lock:
            snapshot = [
                (method, status, self._counts[(method, status)], self._duration_sum[(method, status)])
                for method, status in sorted(self._counts)
            ]
        lines = [
            "# HELP oosys_http_requests_total Total completed HTTP requests.",
            "# TYPE oosys_http_requests_total counter",
        ]
        for method, status, count, _duration in snapshot:
            lines.append(
                f'oosys_http_requests_total{{method="{method}",status_code="{status}"}} {count}'
            )
        lines.extend([
            "# HELP oosys_http_request_duration_seconds_sum Sum of observed request durations.",
            "# TYPE oosys_http_request_duration_seconds_sum counter",
        ])
        for method, status, _count, duration in snapshot:
            lines.append(
                f'oosys_http_request_duration_seconds_sum{{method="{method}",status_code="{status}"}} {duration:.6f}'
            )
        lines.extend([
            "# HELP oosys_http_request_duration_seconds_count Number of duration observations.",
            "# TYPE oosys_http_request_duration_seconds_count counter",
        ])
        for method, status, count, _duration in snapshot:
            lines.append(
                f'oosys_http_request_duration_seconds_count{{method="{method}",status_code="{status}"}} {count}'
            )
        return "\n".join(lines) + "\n"
