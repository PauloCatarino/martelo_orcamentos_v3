"""Nature and orientation constants for the unified piece catalog."""

from __future__ import annotations

MATERIAL = "MATERIAL"
CONJUNTO = "CONJUNTO"
SERVICO = "SERVICO"
FERRAGEM = "FERRAGEM"

PECA_NATUREZA_LABELS = {
    MATERIAL: "Peça física / material",
    CONJUNTO: "Conjunto virtual",
    SERVICO: "Serviço",
    FERRAGEM: "Ferragem / acessório",
}

HORIZONTAL = "HORIZONTAL"
VERTICAL = "VERTICAL"
NEUTRA = "NEUTRA"

PECA_ORIENTACAO_LABELS = {
    HORIZONTAL: "Horizontal",
    VERTICAL: "Vertical",
    NEUTRA: "Neutra / não aplicável",
}


def normalize_peca_natureza(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    return normalized if normalized in PECA_NATUREZA_LABELS else MATERIAL


def normalize_peca_orientacao(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    return normalized if normalized in PECA_ORIENTACAO_LABELS else NEUTRA


def get_peca_natureza_options() -> tuple[tuple[str, str], ...]:
    return tuple(PECA_NATUREZA_LABELS.items())


def get_peca_orientacao_options() -> tuple[tuple[str, str], ...]:
    return tuple(PECA_ORIENTACAO_LABELS.items())


def get_peca_natureza_label(value: str | None) -> str:
    return PECA_NATUREZA_LABELS[normalize_peca_natureza(value)]


def get_peca_orientacao_label(value: str | None) -> str:
    return PECA_ORIENTACAO_LABELS[normalize_peca_orientacao(value)]
