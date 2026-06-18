"""Import checks for the Clientes page."""

from __future__ import annotations


def test_clientes_page_imports() -> None:
    from app.ui.pages.clientes_page import ClientesPage

    assert ClientesPage is not None
