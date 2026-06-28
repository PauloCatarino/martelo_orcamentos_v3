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


def test_orcamentos_page_tem_duplicar_para_versao() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    source = inspect.getsource(OrcamentosPage.__init__)
    assert "Duplicar para Vers\\u00e3o" in source
    assert "duplicar_versao_selecionada" in source
    assert hasattr(OrcamentosPage, "duplicar_versao_selecionada")


def test_orcamentos_page_tem_eliminar_orcamento() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    source = inspect.getsource(OrcamentosPage.__init__)
    assert "Eliminar Or\\u00e7amento" in source
    assert "eliminar_orcamento_selecionado" in source
    assert hasattr(OrcamentosPage, "eliminar_orcamento_selecionado")
