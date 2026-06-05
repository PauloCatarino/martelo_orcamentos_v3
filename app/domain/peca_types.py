"""Piece definition type constants and labels."""

from __future__ import annotations

SIMPLES = "SIMPLES"
COMPOSTA = "COMPOSTA"

PECA_TYPE_LABELS = {
    SIMPLES: "Simples",
    COMPOSTA: "Composta",
}


def get_peca_type_label(tipo_peca: str | None) -> str:
    """Return a friendly label for a piece definition type."""
    return PECA_TYPE_LABELS[normalize_peca_type(tipo_peca)]


def get_peca_type_options() -> tuple[tuple[str, str], ...]:
    """Return piece type options as code/label pairs."""
    return tuple(PECA_TYPE_LABELS.items())


def normalize_peca_type(tipo_peca: str | None) -> str:
    """Normalize a piece definition type code, falling back to SIMPLES."""
    if not tipo_peca:
        return SIMPLES

    normalized = tipo_peca.strip().upper()
    if normalized in PECA_TYPE_LABELS:
        return normalized

    return SIMPLES
