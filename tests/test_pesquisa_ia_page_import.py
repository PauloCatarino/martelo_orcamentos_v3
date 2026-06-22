"""Import checks for the Pesquisa IA page."""

from __future__ import annotations

import inspect
from decimal import Decimal
from types import SimpleNamespace


def test_pesquisa_ia_page_imports() -> None:
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage

    assert PesquisaIAPage is not None


def test_pesquisa_ia_page_table_headers() -> None:
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage

    assert PesquisaIAPage.TABLE_HEADERS == [
        "Fonte",
        "Ref",
        "Descri\u00e7\u00e3o",
        "Fam\u00edlia",
        "Fornecedor",
        "Pre\u00e7o Venda",
        "Pre\u00e7o Custo",
        "Unidade",
        "Stock",
        "Comp",
        "Larg",
        "Esp",
    ]


def test_pesquisa_ia_page_usa_padroes_visuais_e_phc() -> None:
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage

    init_source = inspect.getsource(PesquisaIAPage.__init__)
    carregar_v3_source = inspect.getsource(PesquisaIAPage.carregar_v3)
    carregar_source = inspect.getsource(PesquisaIAPage.carregar_phc)
    recombinar_source = inspect.getsource(PesquisaIAPage._recombinar)
    table_source = inspect.getsource(PesquisaIAPage._preencher_tabela)
    catalogos_source = inspect.getsource(PesquisaIAPage.pesquisar_catalogos)
    preencher_catalogos_source = inspect.getsource(PesquisaIAPage._preencher_catalogos)
    abrir_catalogo_source = inspect.getsource(PesquisaIAPage._abrir_catalogo)

    assert "BarraCabecalho" in init_source
    assert "CampoPesquisa" in init_source
    assert "Pesquisar cat\\u00e1logos (IA)" in init_source
    assert "self.catalogo_table" in init_source
    assert "QHeaderView.ResizeMode.Interactive" in init_source
    assert "ligar_persistencia_larguras" in init_source
    assert "self.carregar_v3()" in init_source
    assert "DefMateriaPrimaService" in carregar_v3_source
    assert "query_phc_materiais" in carregar_source
    assert "except Exception" in carregar_source
    assert "self._v3 + self._phc" in recombinar_source
    assert "tema.cor_zebra(row_index)" in table_source
    assert "resizeColumnsToContents" in table_source
    assert "PesquisaCatalogosService" in inspect.getsource(
        PesquisaIAPage._servico_catalogos
    )
    assert "servico.pesquisar(texto, top_n=30)" in catalogos_source
    assert "python -m scripts.indexar_pesquisa_ia" in catalogos_source
    assert "tema.cor_zebra(row_index)" in preencher_catalogos_source
    assert "Qt.ItemDataRole.UserRole" in preencher_catalogos_source
    assert "QDesktopServices.openUrl" in abrir_catalogo_source
    assert "QUrl.fromLocalFile" in abrir_catalogo_source


def test_pesquisa_ia_corresponde_normaliza_e_procura_varios_campos() -> None:
    from app.ui.pages.pesquisa_ia_page import _corresponde

    linha = {
        "Ref": "MAD001",
        "Descricao": "Aglomerado carvalho",
        "Familia": "MADEIRAS",
        "Fornecedor": "Armaz\u00e9ns Reis",
        "Ref_Fornecedor": "AR-55",
    }

    assert _corresponde(linha, "aglomerado reis") is True
    assert _corresponde(linha, "madeiras ar 55") is True
    assert _corresponde(linha, "ferragem") is False


def test_pesquisa_ia_do_v3_mapeia_materia_local() -> None:
    from app.ui.pages.pesquisa_ia_page import _do_v3

    materia = SimpleNamespace(
        ref_le=" V3-001 ",
        descricao=" Aglomerado ",
        familia_original_excel=" Madeiras ",
        fornecedor=" Fornecedor V3 ",
        preco_liquido=Decimal("12.34"),
        unidade=" m2 ",
        comprimento=Decimal("2440"),
        largura=Decimal("1220"),
        espessura=Decimal("19"),
    )

    linha = _do_v3(materia)

    assert linha["Fonte"] == "V3"
    assert linha["Ref"] == "V3-001"
    assert linha["Descricao"] == "Aglomerado"
    assert linha["Familia"] == "Madeiras"
    assert linha["Fornecedor"] == "Fornecedor V3"
    assert linha["Preco_Venda"] is None
    assert linha["Preco_Custo"] == Decimal("12.34")
    assert linha["Comp"] == Decimal("2440")


def test_pesquisa_ia_do_phc_mapeia_artigo_st() -> None:
    from app.ui.pages.pesquisa_ia_page import _do_phc

    linha = _do_phc(
        {
            "Ref": " PHC-001 ",
            "Descricao": " Dobradi\u00e7a ",
            "Familia": "FF00000",
            "Familia_Nome": "Ferragens",
            "Fornecedor": "Fornecedor PHC",
            "Ref_Fornecedor": "FP-9",
            "Preco_Venda": Decimal("5.50"),
            "Preco_Custo": Decimal("3.25"),
            "Unidade": "UN",
            "Stock": Decimal("8"),
            "Altura": Decimal("100"),
            "Largura": Decimal("20"),
            "Espessura": Decimal("3"),
        }
    )

    assert linha["Fonte"] == "PHC"
    assert linha["Ref"] == "PHC-001"
    assert linha["Descricao"] == "Dobradi\u00e7a"
    assert linha["Familia"] == "Ferragens"
    assert linha["Ref_Fornecedor"] == "FP-9"
    assert linha["Preco_Custo"] == Decimal("3.25")
    assert linha["Comp"] == Decimal("100")
