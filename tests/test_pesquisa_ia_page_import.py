"""Import checks for the Pesquisa IA page."""

from __future__ import annotations

import inspect


def test_pesquisa_ia_page_imports() -> None:
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage

    assert PesquisaIAPage is not None


def test_pesquisa_ia_page_table_headers() -> None:
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage

    assert PesquisaIAPage.TABLE_HEADERS == [
        "Ref",
        "Descri\u00e7\u00e3o",
        "Fam\u00edlia",
        "Fornecedor",
        "Pre\u00e7o Venda",
        "Pre\u00e7o Custo",
        "Unidade",
        "Stock",
        "Alt",
        "Larg",
        "Esp",
    ]


def test_pesquisa_ia_page_usa_padroes_visuais_e_phc() -> None:
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage

    init_source = inspect.getsource(PesquisaIAPage.__init__)
    carregar_source = inspect.getsource(PesquisaIAPage.carregar_phc)
    table_source = inspect.getsource(PesquisaIAPage._preencher_tabela)

    assert "BarraCabecalho" in init_source
    assert "CampoPesquisa" in init_source
    assert "QHeaderView.ResizeMode.Interactive" in init_source
    assert "ligar_persistencia_larguras" in init_source
    assert "query_phc_materiais" in carregar_source
    assert "except Exception" in carregar_source
    assert "tema.cor_zebra(row_index)" in table_source
    assert "resizeColumnsToContents" in table_source


def test_pesquisa_ia_corresponde_normaliza_e_procura_varios_campos() -> None:
    from app.ui.pages.pesquisa_ia_page import _corresponde

    linha = {
        "Ref": "MAD001",
        "Descricao": "Aglomerado carvalho",
        "Familia_Nome": "MADEIRAS",
        "Fornecedor": "Armaz\u00e9ns Reis",
        "Ref_Fornecedor": "AR-55",
    }

    assert _corresponde(linha, "aglomerado reis") is True
    assert _corresponde(linha, "madeiras ar 55") is True
    assert _corresponde(linha, "ferragem") is False
