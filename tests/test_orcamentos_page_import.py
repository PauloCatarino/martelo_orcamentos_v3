"""Import checks for the Orcamentos page."""

from __future__ import annotations


def test_orcamentos_page_imports() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    assert OrcamentosPage is not None
