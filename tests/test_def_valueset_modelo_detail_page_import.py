"""Import checks for the ValueSet model detail page."""

from __future__ import annotations

import inspect


def test_page_imports() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    assert DefValuesetModeloDetailPage is not None


def test_page_accepts_modelo_and_on_back() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    signature = inspect.signature(DefValuesetModeloDetailPage)

    assert "modelo" in signature.parameters
    assert "on_back" in signature.parameters


def test_page_line_headers() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    assert DefValuesetModeloDetailPage.LINHA_HEADERS == [
        "Chave",
        "Opção",
        "Nome opção",
        "Matéria-prima",
        "Padrão",
        "Ordem",
        "Ativo",
    ]


def test_page_has_line_actions() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    for method in (
        "abrir_nova_linha",
        "abrir_editar_linha",
        "alternar_linha_ativa",
        "carregar_linhas",
        "_get_selected_linha",
    ):
        assert hasattr(DefValuesetModeloDetailPage, method)


def test_page_uses_line_service_and_dialog() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    nova = inspect.getsource(DefValuesetModeloDetailPage.abrir_nova_linha)
    assert "DefValuesetModeloLinhaDialog" in nova
    assert "criar_linha" in nova
    assert "definir_como_padrao" in nova

    carregar = inspect.getsource(DefValuesetModeloDetailPage.carregar_linhas)
    assert "DefValuesetModeloLinhaService" in carregar
    assert "listar_linhas_do_modelo" in carregar
