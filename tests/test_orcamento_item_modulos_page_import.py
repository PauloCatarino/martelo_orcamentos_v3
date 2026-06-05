"""Import checks for the Orcamento item modules page."""

from __future__ import annotations

import inspect


def test_orcamento_item_modulos_page_imports() -> None:
    from app.ui.pages.orcamento_item_modulos_page import OrcamentoItemModulosPage

    assert OrcamentoItemModulosPage is not None
    assert hasattr(OrcamentoItemModulosPage, "abrir_modulo_selecionado")
    assert hasattr(OrcamentoItemModulosPage, "_handle_back")
    assert "Abrir M\u00f3dulo" not in OrcamentoItemModulosPage.TABLE_HEADERS


def test_orcamento_item_modulos_page_accepts_item_label_and_back_callback() -> None:
    from app.ui.pages.orcamento_item_modulos_page import OrcamentoItemModulosPage

    parameters = inspect.signature(OrcamentoItemModulosPage).parameters

    assert "item_label" in parameters
    assert "orcamento_codigo" in parameters
    assert "on_back" in parameters
