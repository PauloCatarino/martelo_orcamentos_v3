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
    assert "Peça/Ferragem" in OrcamentoRelatoriosPage.OPERACOES_LINHAS_HEADERS
    assert "Custo atribuído" in OrcamentoRelatoriosPage.OPERACOES_LINHAS_HEADERS

    for method in ("carregar", "_preencher_items", "_preencher_consumos"):
        assert hasattr(OrcamentoRelatoriosPage, method)

    carregar = inspect.getsource(OrcamentoRelatoriosPage.carregar)
    assert "RelatorioConsumosService" in carregar
    assert "resumo_da_versao" in carregar
    assert "get_cliente_da_versao" in carregar
    # Recompute the version before aggregating (8W.1.1).
    assert "recalcular_versao" in carregar
    assert "RelatorioOperacoesService" in carregar
    assert "listar_da_versao" in carregar


def test_relatorio_operacoes_em_linhas_tem_separador_proprio() -> None:
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

    init = inspect.getsource(OrcamentoRelatoriosPage.__init__)
    criar = inspect.getsource(OrcamentoRelatoriosPage._criar_tab_operacoes)
    preencher = inspect.getsource(OrcamentoRelatoriosPage._preencher_operacoes_linhas)
    assert '"Operações"' in init
    assert "mesmo centro" in criar
    assert "(sem operações)" in preencher
    assert "Edição local" in preencher


def test_supervisor_confirma_pdf_e_email_com_saude_da_versao() -> None:
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

    confirmar = inspect.getsource(OrcamentoRelatoriosPage._confirmar_supervisor)
    pdf = inspect.getsource(OrcamentoRelatoriosPage._exportar_pdf)
    email = inspect.getsource(OrcamentoRelatoriosPage._enviar_email)
    assert "executar_versao" in confirmar
    assert "resumir_saude_versao" in confirmar
    assert "< 75" in confirmar
    assert "Rever orçamento" in confirmar
    assert "Assumir e continuar" in confirmar
    assert "_confirmar_supervisor" in pdf
    assert "_confirmar_supervisor" in email


def test_supervisor_abre_operacoes_e_auditoria_no_contexto() -> None:
    from app.ui.main_window import MainWindow
    from app.ui.pages.custeio_auditoria_page import CusteioAuditoriaPage
    from app.ui.pages.orcamento_detail_page import OrcamentoDetailPage
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

    confirmar = inspect.getsource(OrcamentoRelatoriosPage._confirmar_supervisor)
    init = inspect.signature(OrcamentoRelatoriosPage.__init__)
    detalhe = inspect.getsource(OrcamentoDetailPage.__init__)
    janela = inspect.getsource(MainWindow._open_custeio_auditoria_contexto)
    foco = inspect.getsource(CusteioAuditoriaPage.focar_ocorrencia)
    assert "Abrir Operações" in confirmar
    assert "Abrir Auditoria do Custeio" in confirmar
    assert "setCurrentWidget(self.operacoes_tab)" in confirmar
    assert "on_open_custeio_auditoria" in init.parameters
    assert "on_open_custeio_auditoria" in detalhe
    assert 'show_page("custeio_auditoria")' in janela
    assert "focar_ocorrencia" in janela
    assert "codigo_orcamento" in foco
    assert "selectRow" in foco


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


def test_relatorios_nao_stock_ui() -> None:
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

    # Editable check column + budget-cost column.
    assert "Não Stock" in OrcamentoRelatoriosPage.PLACAS_HEADERS
    assert "Custo no Orç." in OrcamentoRelatoriosPage.PLACAS_HEADERS

    for method in ("_on_placa_item_changed", "_preencher_placas"):
        assert hasattr(OrcamentoRelatoriosPage, method)

    # 8W.2-UX: the "Gravar Não-Stock" button is gone — only "Atualizar" remains.
    init = inspect.getsource(OrcamentoRelatoriosPage._criar_tab_consumos)
    assert "Gravar Não-Stock" not in init
    assert "Atualizar" in init
    assert "agravamento_label" in init
    assert not hasattr(OrcamentoRelatoriosPage, "_atualizar_botao_gravar")
    assert not hasattr(OrcamentoRelatoriosPage, "gravar_nao_stock")

    preencher = inspect.getsource(OrcamentoRelatoriosPage._preencher_placas)
    assert "ItemIsUserCheckable" in preencher  # editable checkbox per board
    assert "custo_no_orcamento" in preencher
    assert "agravamento" in preencher
    assert "_tooltip_nao_stock" in preencher  # per-board surcharge tooltip (Part B)

    # Toggling the checkbox persists and recalculates immediately (Part A).
    on_change = inspect.getsource(OrcamentoRelatoriosPage._on_placa_item_changed)
    assert "guardar_nao_stock" in on_change
    assert "carregar" in on_change

    # The tooltip shows this board's surcharge (whole board − theoretical).
    tooltip = inspect.getsource(OrcamentoRelatoriosPage._tooltip_nao_stock)
    assert "custo_placa_inteira" in tooltip
    assert "custo_mp_total" in tooltip


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


def test_dashboards_tab_e_widget() -> None:
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage
    from app.ui.widgets.relatorio_dashboards import DashboardsWidget

    # 8W.3a: o __init__ cria a 3ª aba "Dashboards" com o DashboardsWidget.
    init = inspect.getsource(OrcamentoRelatoriosPage.__init__)
    assert "DashboardsWidget" in init
    assert "self.dashboards" in init
    assert '"Dashboards"' in init

    # carregar() atualiza os gráficos depois de preencher os consumos.
    carregar = inspect.getsource(OrcamentoRelatoriosPage.carregar)
    assert "self.dashboards.atualizar" in carregar

    # O widget expõe o método público de atualização.
    assert hasattr(DashboardsWidget, "atualizar")

    # 8W.3b: a pizza da distribuição de custos é desenhada no atualizar().
    atualizar = inspect.getsource(DashboardsWidget.atualizar)
    assert "dados_distribuicao" in atualizar


def test_formatar_pct_pizza_esconde_fatias_pequenas() -> None:
    # 8W.3c: percentagens abaixo de _PCT_MIN_PIZZA não são desenhadas.
    from app.ui.widgets.relatorio_dashboards import _formatar_pct_pizza

    assert _formatar_pct_pizza(0.6) == ""
    assert _formatar_pct_pizza(3.0) == "3.0%"
    assert _formatar_pct_pizza(17.7) == "17.7%"


def test_detail_page_wires_relatorios_tab() -> None:
    from app.ui.pages.orcamento_detail_page import OrcamentoDetailPage

    source = inspect.getsource(OrcamentoDetailPage.__init__)
    assert "OrcamentoRelatoriosPage" in source
    # The detail-page file uses \uXXXX escapes, so match the ASCII prefix.
    assert "Relat" in source
