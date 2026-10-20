"""Operational endpoint tests for liveness and dependency readiness."""
from sqlalchemy import create_engine

from app.core.config import Settings
from app.main import app, create_app
from tests.asgi_client import asgi_get


def test_health_check() -> None:
    response = asgi_get(app, "/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_is_not_ready_without_database_configuration() -> None:
    custom_app = create_app(Settings(_env_file=None))
    response = asgi_get(custom_app, "/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_readiness_checks_configured_database(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr("app.api.operations.create_database_engine", lambda settings: engine)
    custom_app = create_app(Settings(database_url="sqlite:///:memory:", _env_file=None))
    response = asgi_get(custom_app, "/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}
    engine.dispose()


def test_readiness_reuses_existing_identity_engine(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(
        "app.api.operations.create_database_engine",
        lambda settings: (_ for _ in ()).throw(AssertionError("must reuse existing engine")),
    )
    custom_app = create_app(Settings(database_url="sqlite:///:memory:", _env_file=None))
    custom_app.state.identity_engine = engine
    response = asgi_get(custom_app, "/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}
    assert engine.pool is not None
    engine.dispose()


def test_readiness_failure_is_generic_and_disposes_temporary_engine(monkeypatch) -> None:
    class FailedConnection:
        def __enter__(self):
            raise RuntimeError("sensitive database connection string")

        def __exit__(self, *_args):
            return False

    class FailedEngine:
        disposed = False

        def connect(self):
            return FailedConnection()

        def dispose(self):
            self.disposed = True

    engine = FailedEngine()
    monkeypatch.setattr("app.api.operations.create_database_engine", lambda settings: engine)
    custom_app = create_app(Settings(database_url="sqlite:///:memory:", _env_file=None))
    response = asgi_get(custom_app, "/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert engine.disposed is True


def test_root_endpoint() -> None:
    response = asgi_get(app, "/")
    assert response.status_code == 200
    assert response.json() == {"name": "OOSYS API", "status": "starter"}


def test_app_factory_uses_injected_settings() -> None:
    custom_settings = Settings(
        app_name="Test OOSYS",
        app_version="9.1",
        api_prefix="/custom/v1",
        _env_file=None,
    )
    custom_app = create_app(custom_settings)

    assert custom_app.title == "Test OOSYS"
    assert custom_app.version == "9.1"
    assert asgi_get(custom_app, "/").json()["name"] == "Test OOSYS"
    assert asgi_get(custom_app, "/health").status_code == 200
