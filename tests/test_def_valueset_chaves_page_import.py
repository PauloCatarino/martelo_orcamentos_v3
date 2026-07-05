"""Import checks for the ValueSet keys admin page."""

from __future__ import annotations

import inspect


def test_page_imports() -> None:
    from app.ui.pages.def_valueset_chaves_page import DefValuesetChavesPage

    assert DefValuesetChavesPage is not None


def test_page_is_registered_in_pages() -> None:
    from app.ui.pages import DefValuesetChavesPage

    assert DefValuesetChavesPage is not None


def test_page_headers() -> None:
    from app.ui.pages.def_valueset_chaves_page import DefValuesetChavesPage

    assert DefValuesetChavesPage.TABLE_HEADERS == [
        "Código",
        "Nome",
        "Tipo",
        "Grupo",
        "Sistema",
        "Ordem",
        "Ativo",
    ]


def test_page_has_actions() -> None:
    from app.ui.pages.def_valueset_chaves_page import DefValuesetChavesPage

    for method in (
        "abrir_nova_chave",
        "abrir_editar_chave",
        "alternar_chave_ativa",
        "carregar",
        "_get_selected_chave",
    ):
        assert hasattr(DefValuesetChavesPage, method)


def test_page_loads_via_service() -> None:
    from app.ui.pages.def_valueset_chaves_page import DefValuesetChavesPage

    source = inspect.getsource(DefValuesetChavesPage.carregar)

    assert "DefValuesetChaveService" in source
    assert "listar_chaves" in source


def test_page_actions_use_service_and_dialog() -> None:
    from app.ui.pages.def_valueset_chaves_page import DefValuesetChavesPage

    nova = inspect.getsource(DefValuesetChavesPage.abrir_nova_chave)
    criar = inspect.getsource(DefValuesetChavesPage._criar_chave_from_form_data)
    assert "DefValuesetChaveDialog" in nova
    assert "criar_chave" in criar

    editar = inspect.getsource(DefValuesetChavesPage.abrir_editar_chave)
    assert "editar_chave" in editar
    assert "on_save_as=handle_save_as" in editar
    assert "_criar_chave_from_form_data(form_data)" in editar

    toggle = inspect.getsource(DefValuesetChavesPage.alternar_chave_ativa)
    assert "ativar_chave" in toggle
    assert "desativar_chave" in toggle
    assert "QMessageBox" in toggle
