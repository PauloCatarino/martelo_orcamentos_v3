"""Basic logging configuration."""

from __future__ import annotations

import logging

from app.config.settings import get_settings
from app.core.diario_bordo import configurar_diario


def configure_logging() -> None:
    """Configure root logging for the application."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    # O terminal só existe em desenvolvimento: o executável é empacotado sem
    # consola. O diário de bordo é o que fica mesmo no PC do utilizador.
    configurar_diario(level)

