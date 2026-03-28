"""Startup validation when ENVIRONMENT=production."""

from __future__ import annotations

import logging

from app.config import Settings

logger = logging.getLogger(__name__)

_WEAK_SECRETS = frozenset(
    {
        "",
        "dev-change-me",
        "changeme",
        "secret",
        "password",
        "api_secret",
        "test",
    }
)


def validate_production_settings(settings: Settings) -> None:
    if settings.environment.lower() != "production":
        return
    secret = (settings.api_secret or "").strip()
    if len(secret) < 32:
        raise RuntimeError(
            "ENVIRONMENT=production requires API_SECRET with at least 32 characters."
        )
    if secret.lower() in _WEAK_SECRETS:
        raise RuntimeError(
            "ENVIRONMENT=production requires a non-default API_SECRET value."
        )
    logger.info("Production startup checks passed (API_SECRET strength).")
