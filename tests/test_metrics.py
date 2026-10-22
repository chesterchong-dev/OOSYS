"""Unit tests for bounded request metrics and Prometheus output."""
from app.core.metrics import RequestMetrics


def test_empty_metrics_render_without_unobserved_series() -> None:
    rendered = RequestMetrics().render_prometheus()
    assert "# TYPE oosys_http_requests_total counter" in rendered
    assert "# TYPE oosys_http_request_duration_seconds_sum counter" in rendered
    assert "# TYPE oosys_http_request_duration_seconds_count counter" in rendered
    assert "method=" not in rendered


def test_metrics_bound_method_status_and_duration_labels() -> None:
    metrics = RequestMetrics()
    metrics.observe("GET", 200, 0.125)
    metrics.observe("CONNECT", 42, -3.0)
    rendered = metrics.render_prometheus()

    assert 'method="GET",status_code="200"} 1' in rendered
    assert 'method="GET",status_code="200"} 0.125000' in rendered
    assert 'method="OTHER",status_code="500"} 1' in rendered
    assert 'method="OTHER",status_code="500"} 0.000000' in rendered
    assert "CONNECT" not in rendered
    assert "path=" not in rendered
    assert "tenant=" not in rendered


def test_metric_observations_accumulate() -> None:
    metrics = RequestMetrics()
    metrics.observe("POST", 201, 0.1)
    metrics.observe("POST", 201, 0.2)
    rendered = metrics.render_prometheus()
    assert 'oosys_http_requests_total{method="POST",status_code="201"} 2' in rendered
    assert 'oosys_http_request_duration_seconds_count{method="POST",status_code="201"} 2' in rendered
    assert 'oosys_http_request_duration_seconds_sum{method="POST",status_code="201"} 0.300000' in rendered
