"""Configuration defaults and environment-variable contract tests."""
from app.core.config import Settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "OOSYS API"
    assert settings.api_prefix == "/api/v1"


def test_settings_use_oosys_environment_prefix(monkeypatch) -> None:
    monkeypatch.setenv("OOSYS_APP_NAME", "Test OOSYS")
    settings = Settings(_env_file=None)
    assert settings.app_name == "Test OOSYS"



def test_production_requires_non_empty_rate_limit_secret() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(environment="production", login_rate_limit_secret="", _env_file=None)
