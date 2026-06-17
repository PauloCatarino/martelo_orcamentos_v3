"""Testes dos totais (puros) do relatório de orçamento (fase 8W.4.1).

Importam agora de :mod:`app.domain.relatorio_totais` e confirmam que os mesmos
nomes continuam acessíveis a partir da página de relatórios (re-export).
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.domain.relatorio_totais import (
    IVA_PADRAO_PCT,
    TotaisRelatorio,
    calcular_totais_relatorio,
)


def test_calcular_totais_relatorio() -> None:
    items = [
        SimpleNamespace(quantidade=Decimal("2"), preco_total=Decimal("100")),
        SimpleNamespace(quantidade=Decimal("3"), preco_total=Decimal("50")),
    ]
    totais = calcular_totais_relatorio(items, Decimal("23"))

    assert totais.total_qt == Decimal("5")
    assert totais.subtotal == Decimal("150")
    assert totais.iva_pct == Decimal("23")
    assert totais.iva == Decimal("34.50")        # 150 x 23%
    assert totais.total_geral == Decimal("184.50")


def test_calcular_totais_relatorio_lida_com_none() -> None:
    items = [SimpleNamespace(quantidade=None, preco_total=None)]
    totais = calcular_totais_relatorio(items)

    assert totais.subtotal == Decimal("0")
    assert totais.total_geral == Decimal("0")


def test_iva_padrao_e_23() -> None:
    assert IVA_PADRAO_PCT == Decimal("23")


def test_totais_reexportados_pela_pagina() -> None:
    # A página continua a expor os mesmos objetos (testes/callers existentes).
    from app.ui.pages import orcamento_relatorios_page as pagina

    assert pagina.IVA_PADRAO_PCT is IVA_PADRAO_PCT
    assert pagina.calcular_totais_relatorio is calcular_totais_relatorio
    assert pagina.TotaisRelatorio is TotaisRelatorio
