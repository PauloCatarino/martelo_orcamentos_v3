"""Import checks for the Orcamento detail page."""

from __future__ import annotations


def test_orcamento_detail_page_imports() -> None:
    from app.ui.pages.orcamento_detail_page import OrcamentoDetailPage

    assert OrcamentoDetailPage is not None
