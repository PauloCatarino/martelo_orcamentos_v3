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
        "Ref LE",
        "Descrição orçamento",
        "Unidade",
        "Preço tabela",
        "Margem %",
        "Desconto %",
        "Preço líquido",
        "Desp %",
        "Tipo",
        "Família",
        "Prioridade",
        "Ordem",
        "Editado localmente",
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
        "_abrir_dialog_criar_linha",
        "_criar_linha_from_form_data",
    ):
        assert hasattr(DefValuesetModeloDetailPage, method)


def test_page_uses_line_service_and_dialog() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    criar_dialog = inspect.getsource(DefValuesetModeloDetailPage._abrir_dialog_criar_linha)
    criar_linha = inspect.getsource(DefValuesetModeloDetailPage._criar_linha_from_form_data)
    assert "DefValuesetModeloLinhaDialog" in criar_dialog
    assert "criar_linha" in criar_linha
    assert "editar_linha" not in criar_linha
    assert "prioridade=form_data.prioridade" in criar_linha

    carregar = inspect.getsource(DefValuesetModeloDetailPage.carregar_linhas)
    assert "DefValuesetModeloLinhaService" in carregar
    assert "listar_linhas_do_modelo" in carregar


def test_page_edit_line_has_save_as_create_flow() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    source = inspect.getsource(DefValuesetModeloDetailPage.abrir_editar_linha)

    assert "on_save_as=handle_save_as" in source
    assert "_criar_linha_from_form_data(form_data)" in source
    assert "Linha gravada como nova op" in source


def test_page_formats_percentages() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    source = inspect.getsource(DefValuesetModeloDetailPage._preencher)

    assert "formatar_percentagem" in source
