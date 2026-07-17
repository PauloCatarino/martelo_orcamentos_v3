"""Tests for the composite-piece collapse helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.custeio_colapso import (
    descendentes_por_composta,
    eh_ferragem_auto,
    resumo_composta,
)


@dataclass
class _Linha:
    id: int
    linha_pai_id: int | None
    tipo_linha: str
    custo_total: Decimal | None = None


def _linhas() -> list[_Linha]:
    # Composta (id=100) com uma peça (110) que tem duas ferragens (111, 112),
    # e uma ferragem direta (120). Fora da composta: uma peça (200).
    return [
        _Linha(100, None, "PECA_COMPOSTA"),
        _Linha(110, 100, "PECA", Decimal("7.12")),
        _Linha(111, 110, "FERRAGEM", Decimal("0.00")),
        _Linha(112, 110, "FERRAGEM", Decimal("0.05")),
        _Linha(120, 100, "FERRAGEM", Decimal("4.98")),
        _Linha(200, None, "PECA", Decimal("9.00")),
    ]


def test_descendentes_incluem_netos() -> None:
    mapa = descendentes_por_composta(_linhas())
    assert set(mapa.keys()) == {100}
    assert sorted(mapa[100]) == [110, 111, 112, 120]


def test_linha_sem_composta_nao_aparece_no_mapa() -> None:
    mapa = descendentes_por_composta(_linhas())
    assert 200 not in mapa


def test_resumo_conta_pecas_ferragens_e_soma_custo() -> None:
    linhas = _linhas()
    mapa = descendentes_por_composta(linhas)
    resumo = resumo_composta(linhas, mapa[100])
    assert resumo.n_pecas == 1
    assert resumo.n_ferragens == 3
    assert resumo.custo_total == Decimal("12.15")  # 7.12 + 0 + 0.05 + 4.98


def test_resumo_ignora_custo_none() -> None:
    linhas = [
        _Linha(1, None, "PECA_COMPOSTA"),
        _Linha(2, 1, "FERRAGEM", None),
        _Linha(3, 1, "FERRAGEM", Decimal("2.50")),
    ]
    resumo = resumo_composta(linhas, descendentes_por_composta(linhas)[1])
    assert resumo.n_ferragens == 2
    assert resumo.custo_total == Decimal("2.50")


def test_ferragem_auto_so_dentro_de_composta() -> None:
    dentro = _Linha(111, 110, "FERRAGEM")
    solta = _Linha(120, None, "FERRAGEM")
    peca = _Linha(110, 100, "PECA")
    assert eh_ferragem_auto(dentro) is True
    assert eh_ferragem_auto(solta) is False
    assert eh_ferragem_auto(peca) is False
