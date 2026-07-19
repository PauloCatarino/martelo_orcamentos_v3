"""Pure helpers for collapsing composite pieces in the costing table.

A ``PECA_COMPOSTA`` line is the root of a small tree of child lines (pieces and
rule-filled hardware) linked by ``linha_pai_id``. The UI collapses that tree by
default and shows a summary on the composite row; these helpers compute, without
Qt, which lines belong to each composite, the summary counts/total, and whether a
hardware line is one of the auto (rule-filled) ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.domain.custeio_linha_types import (
    FERRAGEM,
    PECA,
    PECA_COMPOSTA,
    normalize_custeio_linha_type,
)


class _LinhaCusteio(Protocol):
    id: int
    linha_pai_id: int | None
    tipo_linha: str
    custo_total: Decimal | None


@dataclass(frozen=True)
class ResumoComposta:
    """Counts and cost of a composite piece's descendant lines."""

    n_pecas: int
    n_ferragens: int
    custo_total: Decimal


def descendentes_por_composta(
    linhas: list[_LinhaCusteio],
) -> dict[int, list[int]]:
    """Map each composite line id to the ids of all its descendant lines.

    Descendants are found transitively through ``linha_pai_id`` (a piece inside a
    composite may itself have hardware children). Order follows ``linhas`` so the
    UI can hide rows top-to-bottom.
    """
    filhos: dict[int, list[int]] = {}
    for linha in linhas:
        if linha.linha_pai_id is not None:
            filhos.setdefault(linha.linha_pai_id, []).append(linha.id)

    resultado: dict[int, list[int]] = {}
    for linha in linhas:
        if normalize_custeio_linha_type(linha.tipo_linha) != PECA_COMPOSTA:
            continue
        descendentes: list[int] = []
        fila = list(filhos.get(linha.id, []))
        while fila:
            atual = fila.pop(0)
            descendentes.append(atual)
            fila.extend(filhos.get(atual, []))
        resultado[linha.id] = descendentes
    return resultado


def ferragens_associadas_por_peca(
    linhas: list[_LinhaCusteio],
) -> dict[int, list[int]]:
    """Map simple pieces to their directly associated hardware rows.

    A normal catalog piece can have associated hardware without being a
    ``PECA_COMPOSTA`` (for example, a removable shelf with shelf supports).
    Grouping only these direct hardware children keeps the costing table clean
    while leaving the parent piece as the visible, editable line.
    """
    por_id = {linha.id: linha for linha in linhas}
    resultado: dict[int, list[int]] = {}
    for linha in linhas:
        if normalize_custeio_linha_type(linha.tipo_linha) != FERRAGEM:
            continue
        pai_id = linha.linha_pai_id
        pai = por_id.get(pai_id)
        if (
            pai is None
            or pai.linha_pai_id is not None
            or normalize_custeio_linha_type(pai.tipo_linha) != PECA
        ):
            continue
        resultado.setdefault(pai_id, []).append(linha.id)
    return resultado


def resumo_composta(
    linhas: list[_LinhaCusteio], descendentes_ids: list[int]
) -> ResumoComposta:
    """Count pieces/hardware and sum the cost over a composite's descendants."""
    por_id = {linha.id: linha for linha in linhas}
    n_pecas = 0
    n_ferragens = 0
    total = Decimal("0")
    for lid in descendentes_ids:
        linha = por_id.get(lid)
        if linha is None:
            continue
        tipo = normalize_custeio_linha_type(linha.tipo_linha)
        if tipo == PECA:
            n_pecas += 1
        elif tipo == FERRAGEM:
            n_ferragens += 1
        if linha.custo_total is not None:
            total += linha.custo_total
    return ResumoComposta(n_pecas=n_pecas, n_ferragens=n_ferragens, custo_total=total)


def eh_ferragem_auto(linha: _LinhaCusteio) -> bool:
    """True for hardware inside a composite (rule-filled, marked "auto")."""
    return (
        normalize_custeio_linha_type(linha.tipo_linha) == FERRAGEM
        and linha.linha_pai_id is not None
    )
