"""Operation type constants and labels."""

from __future__ import annotations

CORTE = "CORTE"
ORLAGEM = "ORLAGEM"
CNC = "CNC"
REVESTIMENTO = "REVESTIMENTO"
FURACAO = "FURACAO"
RASGO = "RASGO"
COLAGEM = "COLAGEM"
MONTAGEM = "MONTAGEM"
EMBALAMENTO = "EMBALAMENTO"
MAO_OBRA = "MAO_OBRA"
SETUP = "SETUP"
MANUAL = "MANUAL"
OUTRO = "OUTRO"

OPERACAO_TYPE_LABELS = {
    CORTE: "Corte",
    ORLAGEM: "Orlagem",
    CNC: "CNC / Mecaniza\u00e7\u00e3o",
    REVESTIMENTO: "Revestimento de pain\u00e9is",
    FURACAO: "Fura\u00e7\u00e3o",
    RASGO: "Rasgo",
    COLAGEM: "Colagem",
    MONTAGEM: "Montagem",
    EMBALAMENTO: "Embalamento",
    MAO_OBRA: "M\u00e3o de obra",
    SETUP: "Setup",
    MANUAL: "Manual",
    OUTRO: "Outro",
}


def get_operacao_type_label(tipo: str | None) -> str:
    """Return a friendly label for an operation type."""
    return OPERACAO_TYPE_LABELS[normalize_operacao_type(tipo)]


def get_operacao_type_options() -> tuple[tuple[str, str], ...]:
    """Return operation type options as code/label pairs."""
    return tuple(OPERACAO_TYPE_LABELS.items())


def normalize_operacao_type(tipo: str | None) -> str:
    """Normalize an operation type code, falling back to OUTRO."""
    if not tipo:
        return OUTRO

    normalized = tipo.strip().upper()
    if normalized in OPERACAO_TYPE_LABELS:
        return normalized

    return OUTRO
