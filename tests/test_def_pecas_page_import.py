"""Import checks for the DefPecas page."""

from __future__ import annotations

import inspect


def test_def_pecas_page_imports() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    assert DefPecasPage is not None


def test_def_pecas_page_loads_on_init() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    source_names = DefPecasPage.__init__.__code__.co_names

    assert "carregar_pecas" in source_names
    assert "QStackedWidget" in source_names


def test_def_pecas_page_table_headers() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    assert DefPecasPage.TABLE_HEADERS == [
        "C\u00f3digo",
        "Nome",
        "Tipo",
        "Grupo",
        "Orlas",
        "Ativo",
    ]


def test_def_pecas_page_shows_orla_code() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    source = inspect.getsource(DefPecasPage._preencher_tabela)

    assert "format_orla_code" in source


def test_def_pecas_page_supports_open_detail() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    assert hasattr(DefPecasPage, "abrir_nova_peca")
    assert hasattr(DefPecasPage, "abrir_peca_selecionada")
    assert hasattr(DefPecasPage, "_show_detail_page")
    assert hasattr(DefPecasPage, "_voltar_a_lista")
    assert hasattr(DefPecasPage, "_select_peca_by_codigo")
    assert hasattr(DefPecasPage, "_handle_row_double_click")


def test_def_pecas_page_creates_piece_through_dialog_callback() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    source = inspect.getsource(DefPecasPage.abrir_nova_peca)

    assert "NovaDefPecaDialog" in source
    assert "on_save=handle_save" in source
    assert "set_error" in source


def test_def_pecas_page_forwards_orlas_to_service() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    source = inspect.getsource(DefPecasPage.abrir_nova_peca)

    assert "orla_c1=form_data.orla_c1" in source
    assert "orla_c2=form_data.orla_c2" in source
    assert "orla_l1=form_data.orla_l1" in source
    assert "orla_l2=form_data.orla_l2" in source


def test_def_pecas_page_supports_edit() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    assert hasattr(DefPecasPage, "abrir_editar_peca")


def test_def_pecas_page_edit_uses_service_and_dialog() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    source = inspect.getsource(DefPecasPage.abrir_editar_peca)

    assert "EditarDefPecaDialog" in source
    assert "editar_peca" in source
    assert "EditarDefPecaData" in source
    assert "carregar_pecas" in source
    assert "orla_c1=form_data.orla_c1" in source


def test_def_pecas_page_double_click_edits() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    source = inspect.getsource(DefPecasPage._handle_row_double_click)

    assert "abrir_editar_peca" in source
