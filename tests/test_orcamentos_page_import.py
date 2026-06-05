"""Import checks for the Orcamentos page."""

from __future__ import annotations


def test_orcamentos_page_imports() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    assert OrcamentosPage is not None


def test_orcamentos_page_formats_numero_versao_with_two_digits() -> None:
    from app.ui.pages.orcamentos_page import OrcamentosPage

    assert OrcamentosPage._format_numero_versao(1) == "01"
    assert OrcamentosPage._format_numero_versao(2) == "02"
    assert OrcamentosPage._format_numero_versao(3) == "03"
    assert OrcamentosPage._format_numero_versao(10) == "10"
    assert OrcamentosPage._format_numero_versao(12) == "12"
