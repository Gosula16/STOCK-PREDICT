import pytest

from app.config import Settings
from app.core.production import validate_production_settings


def test_production_rejects_short_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_SECRET", "too-short")
    s = Settings()
    with pytest.raises(RuntimeError, match="32"):
        validate_production_settings(s)


def test_development_allows_default_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("API_SECRET", "dev-change-me")
    s = Settings()
    validate_production_settings(s)


def test_production_accepts_long_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv(
        "API_SECRET",
        "a-very-long-production-secret-at-least-32-characters-long",
    )
    s = Settings()
    validate_production_settings(s)
