"""Composite piece component type constants and labels."""

from __future__ import annotations

PECA = "PECA"
FERRAGEM = "FERRAGEM"
ACESSORIO = "ACESSORIO"
SPP = "SPP"
OPERACAO = "OPERACAO"
MAO_OBRA = "MAO_OBRA"

COMPONENTE_TYPE_LABELS = {
    PECA: "Pe\u00e7a",
    FERRAGEM: "Ferragem",
    ACESSORIO: "Acess\u00f3rio",
    SPP: "SPP / Barra / ML",
    OPERACAO: "Opera\u00e7\u00e3o",
    MAO_OBRA: "M\u00e3o de obra",
}


def get_componente_type_label(tipo: str | None) -> str:
    """Return a friendly label for a composite piece component type."""
    return COMPONENTE_TYPE_LABELS[normalize_componente_type(tipo)]


def get_componente_type_options() -> tuple[tuple[str, str], ...]:
    """Return component type options as code/label pairs."""
    return tuple(COMPONENTE_TYPE_LABELS.items())


def normalize_componente_type(tipo: str | None) -> str:
    """Normalize a component type code, falling back to PECA."""
    if not tipo:
        return PECA

    normalized = tipo.strip().upper()
    if normalized in COMPONENTE_TYPE_LABELS:
        return normalized

    return PECA
