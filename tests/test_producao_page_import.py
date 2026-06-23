"""Import checks for the production page."""

from __future__ import annotations

import inspect


def test_producao_page_imports_and_headers() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    assert ProducaoPage.TABLE_HEADERS == [
        "Ano",
        "Processo",
        "Estado",
        "Cliente",
        "Ref Cliente",
        "Obra",
        "Localização",
        "Nº Enc PHC",
        "V. Obra",
        "V. CutRite",
        "Data Início",
        "Data Entrega",
        "Responsável",
        "Tipo Pasta",
    ]


def test_producao_page_init_uses_expected_widgets() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    init_source = inspect.getsource(ProducaoPage.__init__)

    assert "BarraCabecalho" in init_source
    assert "CampoPesquisa" in init_source
    assert "self.table" in init_source
    assert "ligar_persistencia_larguras" in init_source
    assert '"Atualizar"' in init_source
    assert "Converter" not in init_source
    assert '"Novo"' not in init_source
