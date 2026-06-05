"""Import checks for the Orcamento item module detail page."""

from __future__ import annotations

import inspect


def test_orcamento_item_modulo_detail_page_imports() -> None:
    from app.ui.pages.orcamento_item_modulo_detail_page import OrcamentoItemModuloDetailPage

    assert OrcamentoItemModuloDetailPage is not None
    assert hasattr(OrcamentoItemModuloDetailPage, "_handle_back")


def test_orcamento_item_modulo_detail_page_accepts_back_callback() -> None:
    from app.ui.pages.orcamento_item_modulo_detail_page import OrcamentoItemModuloDetailPage

    parameters = inspect.signature(OrcamentoItemModuloDetailPage).parameters

    assert "modulo" in parameters
    assert "on_back" in parameters
