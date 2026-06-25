"""Import checks for the Encomendas Cliente Final (master-detail) tab."""

from __future__ import annotations

import inspect


def test_cliente_final_tab_headers() -> None:
    from app.ui.pages.encomendas_page import EncomendasClienteFinalTab

    assert EncomendasClienteFinalTab.MASTER_HEADERS == [
        "Número",
        "Ano",
        "Cliente",
        "Cliente Abreviado",
        "Contacto",
        "Ref Cliente",
        "Data Receção",
        "Responsável",
        "Data Entrega",
        "Prazo Obrig.",
        "Status",
        "Nº Paletes",
        "Tipo Paletes",
        "Formato Palete",
        "Montagem",
        "Anulada",
        "Observações",
    ]

    assert EncomendasClienteFinalTab.DETAIL_HEADERS == [
        "Ref Obra",
        "Referência",
        "Designação",
        "X",
        "Y",
        "Z",
        "Quantidade",
        "Unidade",
        "Venda",
        "Valor Venda",
        "Unid. Alt",
        "Qtd Alt",
    ]


def test_cliente_final_tab_master_detail_widgets() -> None:
    from app.ui.pages.encomendas_page import EncomendasClienteFinalTab

    source = inspect.getsource(EncomendasClienteFinalTab)

    assert "QSplitter" in source
    assert "CampoPesquisa" in source
    assert 'ligar_persistencia_splitter(self.splitter, "encomendas_cliente_final")' in source
    assert '"encomendas_cf_master"' in source
    assert '"encomendas_cf_itens"' in source
    assert "query_encomendas_cliente_final" in source
    assert "query_itens_encomenda" in source
    assert "Carregar Encomendas (Cliente Final)" in source
    assert "Máx. encomendas" in source
    assert "Máx. itens" in source
    assert "Qt.ItemDataRole.UserRole" in source
    assert "itemSelectionChanged" in source
    assert "Itens Encomenda (Nº" in source
    assert "NoEditTriggers" in source
    assert "SelectRows" in source


def test_page_uses_cliente_final_tab() -> None:
    from app.ui.pages.encomendas_page import EncomendasPage

    source = inspect.getsource(EncomendasPage)
    assert "EncomendasClienteFinalTab" in source
    assert '"Encomendas Cliente Final"' in source
