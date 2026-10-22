"""Configuration defaults and environment-variable contract tests."""
import pytest
from pydantic import ValidationError

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
    with pytest.raises(ValidationError):
        Settings(environment="production", login_rate_limit_secret="", _env_file=None)


def test_cors_validation_rejects_wildcard_and_path() -> None:
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins="*", _env_file=None)
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins="https://portal.example.com/", _env_file=None)
