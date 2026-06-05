"""Component quantity rule constants, labels, and helpers.

In Martelo V3 a piece is analysed as a horizontal piece (Comp / Larg / Esp),
so the main dimension is always treated as length (comprimento), never height
(altura). Legacy "altura" rules are mapped to their "comprimento" equivalents.
"""

from __future__ import annotations

FIXA = "FIXA"
MANUAL = "MANUAL"
POR_COMPRIMENTO = "POR_COMPRIMENTO"
POR_LARGURA = "POR_LARGURA"
POR_COMPRIMENTO_LARGURA = "POR_COMPRIMENTO_LARGURA"
POR_QUANTIDADE_PECA = "POR_QUANTIDADE_PECA"
POR_QUANTIDADE_MODULO = "POR_QUANTIDADE_MODULO"

REGRA_QUANTIDADE_LABELS = {
    FIXA: "Fixa",
    MANUAL: "Manual",
    POR_COMPRIMENTO: "Por comprimento",
    POR_LARGURA: "Por largura",
    POR_COMPRIMENTO_LARGURA: "Por comprimento e largura",
    POR_QUANTIDADE_PECA: "Por quantidade da peça principal",
    POR_QUANTIDADE_MODULO: "Por quantidade do módulo",
}

# Legacy values that used "altura" are mapped to the length-based rules.
REGRA_QUANTIDADE_ALIASES = {
    "POR_ALTURA": POR_COMPRIMENTO,
    "POR_ALTURA_LARGURA": POR_COMPRIMENTO_LARGURA,
}


def get_regra_quantidade_label(regra: str | None) -> str:
    """Return a friendly label for a component quantity rule."""
    return REGRA_QUANTIDADE_LABELS[normalize_regra_quantidade(regra)]


def get_regra_quantidade_options() -> tuple[tuple[str, str], ...]:
    """Return quantity rule options as code/label pairs."""
    return tuple(REGRA_QUANTIDADE_LABELS.items())


def normalize_regra_quantidade(regra: str | None) -> str:
    """Normalize a quantity rule code, falling back to FIXA."""
    if not regra:
        return FIXA

    normalized = regra.strip().upper()
    if not normalized:
        return FIXA

    normalized = REGRA_QUANTIDADE_ALIASES.get(normalized, normalized)

    if normalized in REGRA_QUANTIDADE_LABELS:
        return normalized

    return FIXA
