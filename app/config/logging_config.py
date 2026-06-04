"""Basic logging configuration."""

from __future__ import annotations

import logging

from app.config.settings import get_settings


def configure_logging() -> None:
    """Configure root logging for the application."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

