"""Import checks for the DefPeca detail page."""

from __future__ import annotations

import inspect


def test_def_peca_detail_page_imports() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    assert DefPecaDetailPage is not None


def test_def_peca_detail_page_tabs_are_declared() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    source_names = DefPecaDetailPage.__init__.__code__.co_names

    assert "QTabWidget" in source_names
    assert "_create_dados_gerais_tab" in source_names
    assert "_create_componentes_tab" in source_names


def test_def_peca_detail_page_component_headers() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    assert DefPecaDetailPage.COMPONENTES_HEADERS == [
        "Ordem",
        "Tipo componente",
        "Componente / Refer\u00eancia",
        "Descri\u00e7\u00e3o",
        "Quantidade",
        "Regra quantidade",
        "Obrigat\u00f3rio",
        "Ativo",
    ]


def test_def_peca_detail_page_shows_orlas() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    source = inspect.getsource(DefPecaDetailPage._create_dados_gerais_tab)

    assert "format_orla_code" in source
    assert "get_orla_type_label" in source
    assert "de orlas" in source


def test_def_peca_detail_page_has_component_actions() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    for method in (
        "abrir_novo_componente",
        "abrir_editar_componente",
        "remover_componente",
        "recarregar_componentes",
    ):
        assert hasattr(DefPecaDetailPage, method)


def test_def_peca_detail_page_components_use_service() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    novo = inspect.getsource(DefPecaDetailPage.abrir_novo_componente)
    assert "DefPecaComponenteDialog" in novo
    assert "CriarDefPecaComponenteData" in novo

    editar = inspect.getsource(DefPecaDetailPage.abrir_editar_componente)
    assert "EditarDefPecaComponenteData" in editar

    remover = inspect.getsource(DefPecaDetailPage.remover_componente)
    assert "desativar_componente" in remover
    assert "QMessageBox" in remover


def test_def_peca_detail_page_disables_actions_for_simples() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    source = inspect.getsource(DefPecaDetailPage._create_componentes_tab)

    assert "_is_composta" in source
    assert "setEnabled" in source


def test_def_peca_detail_page_shows_regra_label() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    source = inspect.getsource(DefPecaDetailPage._preencher_componentes)

    assert "get_regra_quantidade_label" in source


def test_def_peca_detail_page_operacoes_headers() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    assert DefPecaDetailPage.OPERACOES_HEADERS == [
        "Ordem",
        "Operação",
        "Tipo",
        "Máquina",
        "Regra cálculo",
        "Quantidade base",
        "Obrigatório",
        "Ativo",
    ]


def test_def_peca_detail_page_operacoes_tab_is_real() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    source_names = DefPecaDetailPage.__init__.__code__.co_names

    assert "_create_operacoes_tab" in source_names


def test_def_peca_detail_page_has_operacao_actions() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    for method in (
        "abrir_nova_operacao",
        "abrir_editar_operacao",
        "alternar_operacao_ativa",
        "recarregar_operacoes",
        "_get_selected_operacao",
    ):
        assert hasattr(DefPecaDetailPage, method)


def test_def_peca_detail_page_operacoes_use_service_and_dialog() -> None:
    from app.ui.pages.def_peca_detail_page import DefPecaDetailPage

    carregar = inspect.getsource(DefPecaDetailPage.recarregar_operacoes)
    assert "DefPecaOperacaoService" in carregar
    assert "listar_operacoes_da_peca" in carregar

    nova = inspect.getsource(DefPecaDetailPage.abrir_nova_operacao)
    assert "DefPecaOperacaoDialog" in nova
    assert "CriarDefPecaOperacaoData" in nova

    editar = inspect.getsource(DefPecaDetailPage.abrir_editar_operacao)
    assert "EditarDefPecaOperacaoData" in editar

    toggle = inspect.getsource(DefPecaDetailPage.alternar_operacao_ativa)
    assert "ativar_operacao_da_peca" in toggle
    assert "desativar_operacao_da_peca" in toggle
    assert "QMessageBox" in toggle
