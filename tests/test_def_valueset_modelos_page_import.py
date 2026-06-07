"""Import checks for the ValueSet models admin page."""

from __future__ import annotations

import inspect


def test_page_imports() -> None:
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage

    assert DefValuesetModelosPage is not None


def test_page_is_registered_in_pages() -> None:
    from app.ui.pages import DefValuesetModelosPage

    assert DefValuesetModelosPage is not None


def test_page_headers() -> None:
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage

    assert DefValuesetModelosPage.TABLE_HEADERS == [
        "Código",
        "Nome",
        "Tipo",
        "Âmbito",
        "Dono/Utilizador",
        "Ativo",
    ]


def test_page_has_actions() -> None:
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage

    for method in (
        "abrir_novo_modelo",
        "abrir_editar_modelo",
        "abrir_modelo_selecionado",
        "alternar_modelo_ativo",
        "carregar_modelos",
    ):
        assert hasattr(DefValuesetModelosPage, method)


def test_page_uses_service_and_dialog() -> None:
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage

    nova = inspect.getsource(DefValuesetModelosPage.abrir_novo_modelo)
    assert "DefValuesetModeloDialog" in nova
    assert "criar_modelo" in nova

    carregar = inspect.getsource(DefValuesetModelosPage.carregar_modelos)
    assert "DefValuesetModeloService" in carregar
    assert "listar_modelos" in carregar

    detail = inspect.getsource(DefValuesetModelosPage._show_detail_page)
    assert "DefValuesetModeloDetailPage" in detail
