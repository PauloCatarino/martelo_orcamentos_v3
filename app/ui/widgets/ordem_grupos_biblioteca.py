"""Persist the per-user order of piece-library groups locally (QSettings)."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QSettings

from app.core.session import app_session

_ORG = "Lanca Encanto"
_APP = "Martelo Orcamentos V3"


def obter_ordens_grupos(grupos: Iterable[str]) -> dict[str, int]:
    """Return saved group positions, defaulting to alphabetical order."""
    grupos_normalizados = sorted({(grupo or "").strip().upper() for grupo in grupos})
    settings = QSettings(_ORG, _APP)
    ordens: dict[str, int] = {}
    for indice, grupo in enumerate(grupos_normalizados, start=1):
        valor = settings.value(_chave(grupo))
        try:
            ordens[grupo] = int(valor) if valor is not None else indice
        except (TypeError, ValueError):
            ordens[grupo] = indice
    return ordens


def ordenar_grupos(grupos: Iterable[str], ordens: dict[str, int] | None = None) -> list[str]:
    """Sort group names by user position, then alphabetically for equal values."""
    unicos = {(grupo or "").strip().upper() for grupo in grupos}
    ordens = ordens or obter_ordens_grupos(unicos)
    return sorted(unicos, key=lambda grupo: (ordens.get(grupo, 9999), grupo))


def guardar_ordens_grupos(ordens: dict[str, int]) -> None:
    """Store the positions for the current authenticated user and machine."""
    settings = QSettings(_ORG, _APP)
    for grupo, ordem in ordens.items():
        settings.setValue(_chave(grupo), max(1, int(ordem)))


def _chave(grupo: str) -> str:
    utilizador = getattr(app_session.current_user, "username", None) or "default"
    seguro = grupo.replace("/", "_")
    return f"biblioteca_pecas/{utilizador}/ordem_grupos/{seguro}"
