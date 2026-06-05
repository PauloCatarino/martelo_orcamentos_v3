"""Import checks for the Orcamentos page."""

from __future__ import annotations


def test_orcamentos_page_imports() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    assert OrcamentosPage is not None


def test_orcamentos_page_loads_on_init() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    source_names = OrcamentosPage.__init__.__code__.co_names

    assert "carregar_orcamentos" in source_names
