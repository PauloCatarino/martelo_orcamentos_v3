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
