"""Scope types for default-margin records (phase 8T.1)."""

from __future__ import annotations

AMBITO_STANDARD = "STANDARD"
AMBITO_CLIENTE = "CLIENTE"
AMBITO_UTILIZADOR = "UTILIZADOR"
AMBITO_CLIENTE_FINAL = "CLIENTE_FINAL"

AMBITOS_MARGENS_PADRAO = (
    AMBITO_STANDARD,
    AMBITO_CLIENTE,
    AMBITO_CLIENTE_FINAL,
    AMBITO_UTILIZADOR,  # legacy records remain readable, never newly selected
)

AMBITO_LABELS = {
    AMBITO_STANDARD: "Standard",
    AMBITO_CLIENTE: "Por Cliente",
    AMBITO_UTILIZADOR: "Por Utilizador",
    AMBITO_CLIENTE_FINAL: "Cliente Final",
}

PERFIL_MARGENS_STANDARD = "STANDARD"
PERFIL_MARGENS_CLIENTE_FINAL = "CLIENTE_FINAL"
PERFIL_MARGENS_CLIENTE = "CLIENTE"
PERFIS_MARGENS = (
    PERFIL_MARGENS_STANDARD,
    PERFIL_MARGENS_CLIENTE_FINAL,
    PERFIL_MARGENS_CLIENTE,
)


def normalizar_perfil_margens(valor: str | None) -> str:
    texto = str(valor or "").strip().upper()
    return texto if texto in PERFIS_MARGENS else PERFIL_MARGENS_STANDARD


def normalize_ambito(valor: str | None) -> str | None:
    """Normalize a margin scope ('STANDARD'/'CLIENTE'/'UTILIZADOR') or None."""
    if valor is None:
        return None

    normalizado = valor.strip().upper()
    if normalizado in AMBITOS_MARGENS_PADRAO:
        return normalizado

    return None
