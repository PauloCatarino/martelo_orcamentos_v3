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
    # Ler, nunca recalcular: quem atualiza os custos é o botão "Atualizar
    # Custos" do orçamento. Aqui só se pergunta se o custeio mexeu desde então.
    assert "recalcular_versao" not in carregar
    assert "custeio_desatualizado" in carregar
    assert "RelatorioOperacoesService" in carregar
    assert "listar_da_versao" in carregar

    # O recálculo continua a existir, mas só quando alguém o pede.
    recalcular = inspect.getsource(OrcamentoRelatoriosPage.recalcular_e_carregar)
    assert "recalcular_versao" in recalcular
    assert "self.carregar()" in recalcular


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
    # A percentagem vai com vírgula, como o resto da aplicação.
    from app.services.dashboard_desenho import _formatar_pct

    assert _formatar_pct(0.6) == ""
    assert _formatar_pct(3.0) == "3,0%"
    assert _formatar_pct(17.7) == "17,7%"


def test_legenda_da_pizza_repete_a_percentagem_da_fatia() -> None:
    # A legenda tem de trazer a MESMA percentagem que está escrita na fatia,
    # senão não há como ligar "27,7%" no gráfico à linha "Placas" na legenda.
    from decimal import Decimal

    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    from app.domain.relatorio_graficos import FatiaPizza, GraficoPizza
    from app.services.dashboard_desenho import desenhar_pizza

    grafico = GraficoPizza(
        titulo="Distribuição de custos",
        fatias=[
            FatiaPizza("Placas", Decimal("75"), Decimal("75")),
            FatiaPizza("Ferragens", Decimal("25"), Decimal("25")),
        ],
        total_venda=Decimal("100"),
    )
    figura = Figure()
    desenhar_pizza(figura, grafico)

    legenda = figura.axes[0].get_legend()
    textos = [t.get_text() for t in legenda.get_texts()]
    assert textos == [
        "Placas — 75,0% — 75,00 €",
        "Ferragens — 25,0% — 25,00 €",
    ]


def test_legenda_da_pizza_usa_o_peso_do_que_esta_desenhado() -> None:
    # Quando uma categoria fica de fora, o matplotlib recalcula as
    # percentagens sobre as fatias desenhadas -- a legenda tem de fazer o
    # mesmo, senão dizia 30% numa fatia onde está escrito 37,5%.
    from decimal import Decimal

    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    from app.domain.relatorio_graficos import FatiaPizza, GraficoPizza
    from app.services.dashboard_desenho import desenhar_pizza

    grafico = GraficoPizza(
        titulo="Distribuição de custos",
        fatias=[
            FatiaPizza("Placas", Decimal("30"), Decimal("30")),
            FatiaPizza("Ferragens", Decimal("50"), Decimal("50")),
        ],
        total_venda=Decimal("100"),   # faltam 20 EUR (categoria filtrada)
    )
    figura = Figure()
    desenhar_pizza(figura, grafico)

    textos = [t.get_text() for t in figura.axes[0].get_legend().get_texts()]
    assert textos[0].startswith("Placas — 37,5%")
    assert textos[1].startswith("Ferragens — 62,5%")


def test_roda_do_rato_em_cima_de_um_grafico_faz_scroll_a_pagina() -> None:
    # A roda do rato tem de fazer scroll à página do dashboard: o canvas do
    # matplotlib ficava com o evento e só arrastando a barra lateral é que a
    # página andava.
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication, QScrollArea

    from app.ui.widgets.relatorio_dashboards import DashboardsWidget

    app = QApplication.instance() or QApplication([])
    widget = DashboardsWidget()
    widget.resize(900, 600)
    widget.show()
    app.processEvents()

    barra = widget.findChild(QScrollArea).verticalScrollBar()
    assert barra.maximum() > 0, "a página tem de ser maior do que a janela"
    assert barra.value() == 0

    canvas = widget._canvases["placas"]
    evento = QWheelEvent(
        QPointF(50, 50),
        canvas.mapToGlobal(QPoint(50, 50)),
        QPoint(0, -120),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(canvas, evento)
    app.processEvents()

    assert barra.value() > 0, "rodar a roda em cima do gráfico tem de descer"
    widget.deleteLater()


def test_detail_page_wires_relatorios_tab() -> None:
    from app.ui.pages.orcamento_detail_page import OrcamentoDetailPage

    source = inspect.getsource(OrcamentoDetailPage.__init__)
    assert "OrcamentoRelatoriosPage" in source
    # The detail-page file uses \uXXXX escapes, so match the ASCII prefix.
    assert "Relat" in source


def test_resumo_de_consumos_mostra_no_maximo_duas_casas_decimais() -> None:
    # As colunas de m2/ml/mm/qt/% do resumo de consumos saíam do cálculo com
    # dez e doze casas decimais e não se liam.
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage as P

    assert P._fmt_m2("6.903333333333") == "6,9 m²"
    assert P._fmt_ml("1058.216666") == "1058,22 ml"
    assert P._fmt_mm("613.333333") == "613,33 mm"
    assert P._fmt_pct("12.5") == "12,5 %"
    assert P._fmt_qt("0.8333333") == "0,83"
    # Sem valor não escreve unidade nenhuma.
    assert P._fmt_m2(None) == ""
    assert P._fmt_mm(None) == ""


def test_tabelas_do_resumo_de_consumos_usam_o_formatador_de_duas_casas() -> None:
    # Guarda contra alguém voltar a pôr format_quantity/format_mm (sem limite
    # de casas) nas quatro tabelas do resumo.
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

    for metodo in (
        OrcamentoRelatoriosPage._preencher_placas,
        OrcamentoRelatoriosPage._preencher_orlas,
        OrcamentoRelatoriosPage._preencher_ferragens,
        OrcamentoRelatoriosPage._preencher_maquinas,
    ):
        fonte = inspect.getsource(metodo)
        assert "format_quantity(" not in fonte
        assert "format_mm(" not in fonte
