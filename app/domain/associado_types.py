"""Configuration constants for pieces associated with another catalog piece."""

from __future__ import annotations

GERAL = "GERAL"
TOPO_1 = "TOPO_1"
TOPO_2 = "TOPO_2"
DOIS_TOPOS = "DOIS_TOPOS"
FACE = "FACE"

ZONA_APLICACAO_LABELS = {
    GERAL: "Geral",
    TOPO_1: "Topo 1",
    TOPO_2: "Topo 2",
    DOIS_TOPOS: "Dois topos",
    FACE: "Face",
}

COMP = "COMP"
LARG = "LARG"
ESP = "ESP"
MEDIDA_TOPO = "MEDIDA_TOPO"

DIMENSAO_REFERENCIA_LABELS = {
    COMP: "Comprimento",
    LARG: "Largura",
    ESP: "Espessura",
    MEDIDA_TOPO: "Medida do topo",
}

TOTAL = "TOTAL"
POR_TOPO = "POR_TOPO"

MODO_QUANTIDADE_LABELS = {
    TOTAL: "Quantidade total",
    POR_TOPO: "Quantidade por topo",
}


def normalize_zona_aplicacao(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    return normalized if normalized in ZONA_APLICACAO_LABELS else GERAL


def normalize_dimensao_referencia(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    return normalized if normalized in DIMENSAO_REFERENCIA_LABELS else COMP


def get_zona_aplicacao_options() -> tuple[tuple[str, str], ...]:
    return tuple(ZONA_APLICACAO_LABELS.items())


def get_dimensao_referencia_options() -> tuple[tuple[str, str], ...]:
    return tuple(DIMENSAO_REFERENCIA_LABELS.items())


def normalize_modo_quantidade(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    return normalized if normalized in MODO_QUANTIDADE_LABELS else TOTAL


def get_modo_quantidade_options() -> tuple[tuple[str, str], ...]:
    return tuple(MODO_QUANTIDADE_LABELS.items())
