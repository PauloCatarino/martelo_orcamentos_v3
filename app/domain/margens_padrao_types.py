"""Scope types for default-margin records (phase 8T.1)."""

from __future__ import annotations

AMBITO_STANDARD = "STANDARD"
AMBITO_CLIENTE = "CLIENTE"
AMBITO_UTILIZADOR = "UTILIZADOR"

AMBITOS_MARGENS_PADRAO = (AMBITO_STANDARD, AMBITO_CLIENTE, AMBITO_UTILIZADOR)

AMBITO_LABELS = {
    AMBITO_STANDARD: "Standard",
    AMBITO_CLIENTE: "Por Cliente",
    AMBITO_UTILIZADOR: "Por Utilizador",
}


def normalize_ambito(valor: str | None) -> str | None:
    """Normalize a margin scope ('STANDARD'/'CLIENTE'/'UTILIZADOR') or None."""
    if valor is None:
        return None

    normalizado = valor.strip().upper()
    if normalizado in AMBITOS_MARGENS_PADRAO:
        return normalizado

    return None
