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
    assert "QTreeWidget" in source_names


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


def test_def_pecas_page_forwards_valuesets_to_service() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    create_source = inspect.getsource(DefPecasPage.abrir_nova_peca)
    edit_source = inspect.getsource(DefPecasPage.abrir_editar_peca)

    for source in (create_source, edit_source):
        assert "chave_valueset_material=form_data.chave_valueset_material" in source
        assert "permite_acabamento=form_data.permite_acabamento" in source
        assert (
            "chave_valueset_acabamento_sup=form_data.chave_valueset_acabamento_sup"
            in source
        )
        assert (
            "chave_valueset_acabamento_inf=form_data.chave_valueset_acabamento_inf"
            in source
        )


def test_def_pecas_page_supports_edit() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    assert hasattr(DefPecasPage, "abrir_editar_peca")


def test_def_pecas_page_supports_duplicate() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    init_source = inspect.getsource(DefPecasPage.__init__)
    duplicate_source = inspect.getsource(DefPecasPage.duplicar_peca_selecionada)

    assert "duplicate_button" in init_source
    assert "Duplicar Pe" in init_source
    assert hasattr(DefPecasPage, "duplicar_peca_selecionada")
    assert "QInputDialog.getText" in duplicate_source
    assert "duplicar_peca" in duplicate_source
    assert "carregar_pecas" in duplicate_source


def test_def_pecas_page_supports_active_toggle_and_inactive_filter() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    init_source = inspect.getsource(DefPecasPage.__init__)
    carregar_source = inspect.getsource(DefPecasPage.carregar_pecas)
    toggle_source = inspect.getsource(DefPecasPage.alternar_peca_ativa)

    assert "toggle_ativo_button" in init_source
    assert "Ativar/Desativar" in init_source
    assert "mostrar_inativas_check" in init_source
    assert "QMessageBox.question" in toggle_source
    assert "desativar_peca" in toggle_source
    assert "ativar_peca" in toggle_source
    assert "not self.mostrar_inativas_check.isChecked()" in carregar_source
    assert "if peca.ativo" in carregar_source


def test_def_pecas_page_has_resizable_columns() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    init_source = inspect.getsource(DefPecasPage.__init__)

    assert "QHeaderView.ResizeMode.Interactive" in init_source
    assert "setStretchLastSection(False)" in init_source
    assert "QHeaderView.ResizeMode.Stretch" not in init_source


def test_def_pecas_page_supports_tree_view() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    init_source = inspect.getsource(DefPecasPage.__init__)
    preencher_arvore = inspect.getsource(DefPecasPage._preencher_arvore)
    get_selected = inspect.getsource(DefPecasPage._get_selected_peca)

    assert "toggle_vista_button" in init_source
    assert "Ver em" in init_source
    assert "lista_stack" in init_source
    assert "QTreeWidgetItem" in preencher_arvore
    assert "SEM GRUPO" in preencher_arvore
    assert "format_orla_code" in preencher_arvore
    assert "COMPOSTA" in preencher_arvore
    assert "Qt.ItemDataRole.UserRole" in preencher_arvore
    assert "expandAll" in preencher_arvore
    assert "_pecas_by_id" in get_selected
    assert "currentItem" in get_selected


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
