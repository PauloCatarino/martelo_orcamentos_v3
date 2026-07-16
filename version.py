"""Versao da aplicacao Martelo Orcamentos V3.

Usada pelo executavel/instalador para identificar que versao cada colega
tem instalada quando reportar problemas na fase de testes.
"""

APP_VERSION = "0.9.0"
APP_STAGE = "beta"


def version_completa() -> str:
    """Ex.: '0.9.0-beta' (ou '0.9.0' se APP_STAGE vazio)."""
    return f"{APP_VERSION}-{APP_STAGE}" if APP_STAGE else APP_VERSION
