"""Import checks for the Encomendas (PHC) page."""

from __future__ import annotations

import inspect


def test_encomendas_page_imports_and_tabs() -> None:
    from app.ui.pages.encomendas_page import EncomendasPage, EncomendasPHCTab

    assert EncomendasPHCTab is not None

    page_source = inspect.getsource(EncomendasPage)
    assert "BarraCabecalho" in page_source
    assert "QTabWidget" in page_source
    assert "EncomendasPHCTab" in page_source
    assert '"Encomendas PHC"' in page_source
    assert '"Encomendas Cliente Final"' in page_source
    assert '"Diagnóstico PHC"' in page_source
    assert "Em desenvolvimento" in page_source


def test_encomendas_phc_tab_headers_and_widgets() -> None:
    from app.ui.pages.encomendas_page import EncomendasPHCTab

    assert EncomendasPHCTab.TABLE_HEADERS == [
        "Cliente",
        "Cliente Abreviado",
        "Enc Nº",
        "Num PHC",
        "Ref PHC",
        "Telefone",
        "Ref Cliente",
        "Descrição Artigo",
        "Data Encomenda",
        "Data Entrega",
    ]

    source = inspect.getsource(EncomendasPHCTab)
    assert "CampoPesquisa" in source
    assert "ligar_persistencia_larguras" in source
    assert '"encomendas_phc"' in source
    assert "query_encomendas_phc" in source
    assert "Carregar Encomendas (PHC)" in source
    assert "Ano mínimo" in source
    assert "Máx. linhas" in source
    assert "QSpinBox" in source
    assert "NoEditTriggers" in source
    assert "SelectRows" in source
