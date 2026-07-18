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
        "_criar_modelo_from_form_data",
        "_criar_modelo_data_from_form_data",
    ):
        assert hasattr(DefValuesetModelosPage, method)


def test_page_uses_service_and_dialog() -> None:
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage

    nova = inspect.getsource(DefValuesetModelosPage.abrir_novo_modelo)
    criar = inspect.getsource(DefValuesetModelosPage._criar_modelo_from_form_data)
    editar = inspect.getsource(DefValuesetModelosPage.abrir_editar_modelo)
    assert "DefValuesetModeloDialog" in nova
    assert "criar_modelo" in criar
    assert "on_save_as=handle_save_as" in editar
    assert "duplicar_modelo" in editar

    carregar = inspect.getsource(DefValuesetModelosPage.carregar_modelos)
    assert "DefValuesetModeloService" in carregar
    assert "listar_modelos" in carregar

    detail = inspect.getsource(DefValuesetModelosPage._show_detail_page)
    assert "DefValuesetModeloDetailPage" in detail
    assert "on_modelo_duplicado" in detail

    duplicado = inspect.getsource(DefValuesetModelosPage._abrir_modelo_duplicado)
    assert "_show_detail_page" in duplicado
    assert "status_label.setText" in duplicado
def test_modelos_ocultam_inativos_e_guardam_larguras() -> None:
    import inspect
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage

    init = inspect.getsource(DefValuesetModelosPage.__init__)
    classe = inspect.getsource(DefValuesetModelosPage)
    carregar = inspect.getsource(DefValuesetModelosPage.carregar_modelos)
    assert "mostrar_inativos_check" in init
    assert "QHeaderView.ResizeMode.Interactive" in classe
    assert "ligar_persistencia_larguras" in classe
    assert "if modelo.ativo" in carregar


def test_modelos_usam_dois_separadores() -> None:
    import inspect
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage

    init = inspect.getsource(DefValuesetModelosPage.__init__)
    assert "QTabWidget" in init
    assert "tabela_utilizador" in init
    assert "tabela_globais" in init

    carregar = inspect.getsource(DefValuesetModelosPage.carregar_modelos)
    assert "listar_modelos_para_separadores" in carregar
