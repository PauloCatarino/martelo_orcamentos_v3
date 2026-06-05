"""Import checks for the DefPecas page."""

from __future__ import annotations


def test_def_pecas_page_imports() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    assert DefPecasPage is not None


def test_def_pecas_page_loads_on_init() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    source_names = DefPecasPage.__init__.__code__.co_names

    assert "carregar_pecas" in source_names


def test_def_pecas_page_table_headers() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    assert DefPecasPage.TABLE_HEADERS == [
        "C\u00f3digo",
        "Nome",
        "Tipo",
        "Grupo",
        "Ativo",
    ]
