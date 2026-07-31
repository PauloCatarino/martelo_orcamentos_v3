"""Basic logging configuration."""

from __future__ import annotations

import logging

from app.config.settings import get_settings
from app.core.diario_bordo import configurar_diario

#: Caminho opcional do registo, editável em Configurações → Caminhos do Sistema.
KEY_FICHEIRO_LOG = "ficheiro_log"


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
    configurar_diario(level, preferido=_ficheiro_log_configurado())


def _ficheiro_log_configurado() -> str:
    """Ler o 'Ficheiro de log' de Caminhos do Sistema (vazio = automático).

    Corre antes do login e a base de dados pode não estar acessível — nesse
    caso o registo arranca à mesma, no sítio por omissão.
    """
    try:
        from app.db.session import SessionLocal
        from app.services.system_setting_service import SystemSettingService

        with SessionLocal() as session:
            return (SystemSettingService(session).obter_valor(KEY_FICHEIRO_LOG, "") or "").strip()
    except Exception:  # noqa: BLE001 - o registo nunca pode impedir o arranque
        return ""

