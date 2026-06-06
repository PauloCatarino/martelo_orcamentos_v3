"""Import checks for the Orcamento detail page."""

from __future__ import annotations


import inspect


def test_orcamento_detail_page_imports() -> None:
    from app.ui.pages.orcamento_detail_page import OrcamentoDetailPage

    assert OrcamentoDetailPage is not None


def test_orcamento_detail_page_custeio_tab_is_real() -> None:
    from app.ui.pages.orcamento_detail_page import OrcamentoDetailPage

    source = inspect.getsource(OrcamentoDetailPage.__init__)

    assert "OrcamentoCusteioPage" in source
    assert '"Custeio"' in source
