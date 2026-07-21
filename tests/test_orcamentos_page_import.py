"""Import checks for the Orcamentos page."""

from __future__ import annotations

import inspect


def test_orcamentos_page_imports() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    assert OrcamentosPage is not None


def test_orcamentos_page_loads_on_init() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    source_names = OrcamentosPage.__init__.__code__.co_names

    assert "carregar_orcamentos" in source_names


def test_orcamentos_page_duplicar_versao_movido_para_editar() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    # The toolbar button was removed; duplicating a version now lives inside
    # the Editar Orçamento dialog and is handled by this helper.
    init_source = inspect.getsource(OrcamentosPage.__init__)
    assert "duplicate_version_button" not in init_source
    assert hasattr(OrcamentosPage, "_duplicar_versao_com_dados")
    assert not hasattr(OrcamentosPage, "duplicar_versao_selecionada")

    editar_source = inspect.getsource(OrcamentosPage.editar_orcamento_selecionado)
    assert "duplicar_versao_requested" in editar_source
    assert "get_proxima_versao" in editar_source


def test_orcamentos_page_tem_eliminar_orcamento() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    source = inspect.getsource(OrcamentosPage.__init__)
    assert "Eliminar Or\\u00e7amento" in source
    assert "eliminar_orcamento_selecionado" in source
    assert hasattr(OrcamentosPage, "eliminar_orcamento_selecionado")
