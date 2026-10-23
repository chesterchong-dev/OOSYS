"""Typed environment-backed settings for OOSYS."""
from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings; secrets must be supplied outside source control."""

    app_name: str = "OOSYS API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: SecretStr | None = None
    allow_self_registration: bool = False
    session_ttl_hours: int = Field(default=12, ge=1, le=168)
    login_max_attempts: int = Field(default=8, ge=3, le=50)
    login_window_minutes: int = Field(default=15, ge=1, le=1440)
    login_rate_limit_secret: SecretStr | None = Field(default=None, repr=False)
    cors_allowed_origins: str = ""
    metrics_enabled: bool = False
    metrics_token: SecretStr | None = Field(default=None, repr=False)
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = Field(default=None, repr=False)
    email_from: str | None = None
    password_reset_url: str | None = None
    invitation_accept_url: str | None = None

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if "*" in origins:
            raise ValueError("Wildcard CORS origins are not supported; specify explicit origins")
        for origin in origins:
            try:
                parsed = urlsplit(origin)
                # Accessing .port validates the numeric range and syntax.
                parsed.port
            except ValueError as exc:
                raise ValueError("CORS origins must contain a valid host and port") from exc
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "CORS origins must be HTTP(S) scheme and host only, without credentials, path, query or fragment"
                )
        return ",".join(origins)

    @model_validator(mode="after")
    def validate_runtime_secrets(self):
        if self.environment.strip().lower() == "production" and (
            self.login_rate_limit_secret is None
            or not self.login_rate_limit_secret.get_secret_value().strip()
        ):
            raise ValueError("OOSYS_LOGIN_RATE_LIMIT_SECRET is required in production")
        if self.metrics_enabled and (
            self.metrics_token is None
            or len(self.metrics_token.get_secret_value()) < 32
        ):
            raise ValueError(
                "OOSYS_METRICS_TOKEN must contain at least 32 characters when metrics are enabled"
            )
        return self

    model_config = SettingsConfigDict(
        env_prefix="OOSYS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for dependency injection and app construction."""
    return Settings()
