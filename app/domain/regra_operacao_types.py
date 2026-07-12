"""Operation calculation rule constants, labels, and helpers."""

from __future__ import annotations

FIXA = "FIXA"
POR_PECA = "POR_PECA"
POR_QUANTIDADE = "POR_QUANTIDADE"
POR_ML = "POR_ML"
POR_M2 = "POR_M2"
POR_AREA_FACE = "POR_AREA_FACE"
POR_ORLAS = "POR_ORLAS"
POR_FURACAO = "POR_FURACAO"
POR_SETUP = "POR_SETUP"
RASGO_CNC = "RASGO_CNC"
MANUAL = "MANUAL"

REGRA_OPERACAO_LABELS = {
    FIXA: "Fixa",
    POR_PECA: "Por peça",
    POR_QUANTIDADE: "Por quantidade",
    POR_ML: "Por metro linear",
    POR_M2: "Por metro quadrado",
    POR_AREA_FACE: "Por área da face",
    POR_ORLAS: "Por orlas",
    POR_FURACAO: "Por furação",
    POR_SETUP: "Por setup",
    RASGO_CNC: "Rasgo CNC por comprimento geométrico",
    MANUAL: "Manual",
}


def get_regra_operacao_label(regra: str | None) -> str:
    """Return a friendly label for an operation calculation rule."""
    return REGRA_OPERACAO_LABELS[normalize_regra_operacao(regra)]


def get_regra_operacao_options() -> tuple[tuple[str, str], ...]:
    """Return operation calculation rule options as code/label pairs."""
    return tuple(REGRA_OPERACAO_LABELS.items())


def normalize_regra_operacao(regra: str | None) -> str:
    """Normalize an operation calculation rule code, falling back to FIXA."""
    if not regra:
        return FIXA

    normalized = regra.strip().upper()
    if normalized in REGRA_OPERACAO_LABELS:
        return normalized

    return FIXA
