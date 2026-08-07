"""Regras comuns para prioridades de linhas ValueSet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


class LinhaComPrioridade(Protocol):
    id: int
    chave: str
    prioridade: int | None
    ativo: bool


@dataclass(frozen=True)
class ConflitoPrioridade:
    """Prioridade repetida por linhas ativas da mesma chave."""

    chave: str
    prioridade: int
    sugestao: int


def detetar_conflito_prioridade(
    linha_destino: LinhaComPrioridade,
    linhas: Iterable[LinhaComPrioridade],
) -> ConflitoPrioridade | None:
    """Deteta conflito e propõe a menor prioridade positiva ainda livre."""
    if not linha_destino.ativo or linha_destino.prioridade is None:
        return None

    mesma_chave = [
        linha
        for linha in linhas
        if linha.ativo and linha.chave == linha_destino.chave
    ]
    if not any(
        linha.id != linha_destino.id
        and linha.prioridade == linha_destino.prioridade
        for linha in mesma_chave
    ):
        return None

    usadas = {
        linha.prioridade
        for linha in mesma_chave
        if linha.prioridade is not None and linha.prioridade > 0
    }
    sugestao = 1
    while sugestao in usadas:
        sugestao += 1

    return ConflitoPrioridade(
        chave=linha_destino.chave,
        prioridade=linha_destino.prioridade,
        sugestao=sugestao,
    )
