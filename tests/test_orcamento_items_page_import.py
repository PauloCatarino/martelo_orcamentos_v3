"""Import checks for the Orcamento items page."""

from __future__ import annotations

import inspect


def test_orcamento_items_page_imports() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    assert OrcamentoItemsPage is not None


def test_orcamento_items_page_accepts_on_item_selected() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    signature = inspect.signature(OrcamentoItemsPage)

    assert "on_item_selected" in signature.parameters
