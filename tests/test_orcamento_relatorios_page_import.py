"""Import/logic checks for the budget reports page (phase 8W.1)."""

from __future__ import annotations

import inspect
from decimal import Decimal
from types import SimpleNamespace


def test_orcamento_relatorios_page_imports() -> None:
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

    assert OrcamentoRelatoriosPage.ITEMS_HEADERS == [
        "Item", "Código", "Descrição", "Altura", "Largura", "Profundidade",
        "Unidade", "Qt", "Preço Unitário", "Preço Total",
    ]
    # The four consumption tables follow the V2 columns.
    assert "Qt.Pla" in OrcamentoRelatoriosPage.PLACAS_HEADERS
    assert "Não Stock" in OrcamentoRelatoriosPage.PLACAS_HEADERS
    assert OrcamentoRelatoriosPage.MAQUINAS_HEADERS == [
        "Operação", "Custo Total", "ML Corte", "ML Orlado", "Nº Peças",
    ]

    for method in ("carregar", "_preencher_items", "_preencher_consumos"):
        assert hasattr(OrcamentoRelatoriosPage, method)

    carregar = inspect.getsource(OrcamentoRelatoriosPage.carregar)
    assert "RelatorioConsumosService" in carregar
    assert "resumo_da_versao" in carregar
    assert "get_cliente_da_versao" in carregar
    # Recompute the version before aggregating (8W.1.1).
    assert "recalcular_versao" in carregar


def test_relatorios_consumos_nota_e_tooltips() -> None:
    from app.ui.pages.orcamento_relatorios_page import (
        _NOTA_CONSUMOS_TOPO,
        OrcamentoRelatoriosPage,
    )

    # Prominent note: consumptions are the WHOLE-budget totals.
    assert "TOTAL do orçamento" in _NOTA_CONSUMOS_TOPO
    assert "quantidade de cada item" in _NOTA_CONSUMOS_TOPO

    consumos = inspect.getsource(OrcamentoRelatoriosPage._criar_tab_consumos)
    assert "_NOTA_CONSUMOS_TOPO" in consumos
    assert "ORLAS_TOOLTIPS" in consumos
    assert "FERRAGENS_TOOLTIPS" in consumos

    # 3-block tooltips on the calculated columns (description / formula / values).
    assert "Qt.Pla" in OrcamentoRelatoriosPage.PLACAS_TOOLTIPS
    assert "Fórmula:" in OrcamentoRelatoriosPage.PLACAS_TOOLTIPS["Qt.Pla"]
    assert "→ 2 placas" in OrcamentoRelatoriosPage.PLACAS_TOOLTIPS["Qt.Pla"]
    assert "Qt" in OrcamentoRelatoriosPage.FERRAGENS_TOOLTIPS
    assert "ML Tot" in OrcamentoRelatoriosPage.ORLAS_TOOLTIPS
    assert "Custo Total" in OrcamentoRelatoriosPage.MAQUINAS_TOOLTIPS


def test_calcular_totais_relatorio() -> None:
    from app.ui.pages.orcamento_relatorios_page import calcular_totais_relatorio

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
    from app.ui.pages.orcamento_relatorios_page import calcular_totais_relatorio

    items = [SimpleNamespace(quantidade=None, preco_total=None)]
    totais = calcular_totais_relatorio(items)

    assert totais.subtotal == Decimal("0")
    assert totais.total_geral == Decimal("0")


def test_iva_padrao_e_23() -> None:
    from app.ui.pages.orcamento_relatorios_page import IVA_PADRAO_PCT

    assert IVA_PADRAO_PCT == Decimal("23")


def test_detail_page_wires_relatorios_tab() -> None:
    from app.ui.pages.orcamento_detail_page import OrcamentoDetailPage

    source = inspect.getsource(OrcamentoDetailPage.__init__)
    assert "OrcamentoRelatoriosPage" in source
    # The detail-page file uses \uXXXX escapes, so match the ASCII prefix.
    assert "Relat" in source
