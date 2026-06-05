"""Import checks for the DefPeca detail page."""

from __future__ import annotations


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
