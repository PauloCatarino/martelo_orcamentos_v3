"""Import checks for the Orcamento item modules page."""

from __future__ import annotations


def test_orcamento_item_modulos_page_imports() -> None:
    from app.ui.pages.orcamento_item_modulos_page import OrcamentoItemModulosPage

    assert OrcamentoItemModulosPage is not None
