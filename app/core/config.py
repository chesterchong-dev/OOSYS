"""Typed environment-backed settings for OOSYS."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings; secrets must be supplied outside source control."""

    app_name: str = "OOSYS API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"

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
