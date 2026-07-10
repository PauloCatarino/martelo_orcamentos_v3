"""Explicit actions used to compose ValueSet variant operations."""

from __future__ import annotations

ADICIONAR = "ADICIONAR"
SUBSTITUIR = "SUBSTITUIR"
DESATIVAR = "DESATIVAR"

OPERACAO_ACAO_LABELS = {
    ADICIONAR: "Adicionar",
    SUBSTITUIR: "Substituir operação do mesmo tipo",
    DESATIVAR: "Desativar esta operação",
}


def normalize_operacao_acao(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    return normalized if normalized in OPERACAO_ACAO_LABELS else ADICIONAR


def get_operacao_acao_options() -> tuple[tuple[str, str], ...]:
    return tuple(OPERACAO_ACAO_LABELS.items())


def get_operacao_acao_label(value: str | None) -> str:
    return OPERACAO_ACAO_LABELS[normalize_operacao_acao(value)]
