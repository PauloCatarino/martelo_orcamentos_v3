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
        "Ref Fornec",
        "Data pre\u00e7o",
    ]


def test_pesquisa_ia_page_usa_padroes_visuais_e_phc() -> None:
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage

    init_source = inspect.getsource(PesquisaIAPage.__init__)
    carregar_v3_source = inspect.getsource(PesquisaIAPage.carregar_v3)
    carregar_source = inspect.getsource(PesquisaIAPage.carregar_phc)
    recombinar_source = inspect.getsource(PesquisaIAPage._recombinar)
    table_source = inspect.getsource(PesquisaIAPage._preencher_tabela)
    catalogos_source = inspect.getsource(PesquisaIAPage.pesquisar_catalogos)
    resposta_source = inspect.getsource(PesquisaIAPage.gerar_resposta)
    carregar_refs_source = inspect.getsource(PesquisaIAPage.carregar_referencias)
    preencher_refs_source = inspect.getsource(PesquisaIAPage._preencher_referencias)
    preencher_catalogos_source = inspect.getsource(PesquisaIAPage._preencher_catalogos)
    abrir_catalogo_source = inspect.getsource(PesquisaIAPage._abrir_catalogo)

    assert "BarraCabecalho" in init_source
    assert "CampoPesquisa" in init_source
    assert "Pesquisar cat\\u00e1logos (IA)" in init_source
    assert "Carregar refer\\u00eancias (placas)" in init_source
    assert "Gerar resposta IA" in init_source
    assert "self.referencias_table" in init_source
    assert "ESPESSURAS" in init_source
    assert "pesquisa_ia_referencias" in init_source
    assert "self.catalogo_table" in init_source
    assert "pesquisa_ia_catalogos" in init_source
    assert "self.resposta_text = QTextEdit()" in init_source
    assert "self._ultimos_catalogos" in init_source
    assert "self._filtrados_estrutural" in init_source
    assert "self._referencias_todas" in init_source
    assert "self._referencias_filtradas" in init_source
    assert "QHeaderView.ResizeMode.Interactive" in init_source
    assert "ligar_persistencia_larguras" in init_source
    assert "self.carregar_v3()" in init_source
    assert "DefMateriaPrimaService" in carregar_v3_source
    assert "query_phc_materiais" in carregar_source
    assert "listar_referencias(session)" in carregar_refs_source
    assert "self.referencias_button.setEnabled(False)" in carregar_refs_source
    assert "except Exception" in carregar_source
    assert "self._v3 + self._phc" in recombinar_source
    assert "tema.cor_zebra(row_index)" in table_source
    assert "self._filtrados_estrutural = filtrados" in inspect.getsource(
        PesquisaIAPage.aplicar_pesquisa
    )
    assert "self._referencias_filtradas = referencias" in inspect.getsource(
        PesquisaIAPage.aplicar_pesquisa
    )
    assert "_ref_corresponde" in inspect.getsource(PesquisaIAPage.aplicar_pesquisa)
    assert "resizeColumnsToContents" in table_source
    assert "tema.cor_zebra(row_index)" in preencher_refs_source
    assert "referencia.precos.get" in preencher_refs_source
    assert "str(resultado.get(\"Ref_Fornecedor\") or \"\")" in table_source
    assert "str(resultado.get(\"Data_Preco\") or \"\")" in table_source
    assert "PesquisaCatalogosService" in inspect.getsource(
        PesquisaIAPage._servico_catalogos
    )
    assert "servico.pesquisar(texto, top_n=30)" in catalogos_source
    assert "self._ultimos_catalogos = resultados" in catalogos_source
    assert "python -m scripts.indexar_pesquisa_ia" in catalogos_source
    assert "RespostaIAService(session).gerar(pergunta, contexto)" in resposta_source
    assert "self.resposta_text.setPlainText" in resposta_source
    assert "ARTIGOS (mat\\u00e9rias-primas PHC/V3)" in resposta_source
    assert "REFER\\u00caNCIAS DE PLACAS" in resposta_source
    assert "Pre\\u00e7os por espessura" in resposta_source
    assert "TRECHOS DE CAT\\u00c1LOGOS" in resposta_source
    assert "format_currency" in resposta_source
    assert "format_quantity" in resposta_source
    assert "self._filtrados_estrutural[:15]" in resposta_source
    assert "self._referencias_filtradas[:10]" in resposta_source
    assert "self._ultimos_catalogos[:8]" in resposta_source
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


def test_pesquisa_ia_ref_corresponde_normaliza_e_procura_varios_campos() -> None:
    from app.services.placas_referencias_service import LinhaReferencia
    from app.ui.pages.pesquisa_ia_page import _ref_corresponde

    linha = LinhaReferencia(
        folha="Egger",
        referencia="W1000",
        st_acab="ST9",
        nome_design="Branco Premium",
        grupo="Lisos",
        tipo="MDF",
        fornecedor="Fornecedor A",
        precos={"8mm": "14,60 \u20ac"},
    )

    assert _ref_corresponde(linha, "branco fornecedor") is True
    assert _ref_corresponde(linha, "w1000 st9") is True
    assert _ref_corresponde(linha, "dobradica") is False


def test_pesquisa_ia_do_v3_mapeia_materia_local() -> None:
    from app.ui.pages.pesquisa_ia_page import _do_v3

    materia = SimpleNamespace(
        ref_le=" V3-001 ",
        descricao=" Aglomerado ",
        familia_original_excel=" Madeiras ",
        fornecedor=" Fornecedor V3 ",
        referencia_fornecedor=" REF-F-V3 ",
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
    assert linha["Ref_Fornecedor"] == "REF-F-V3"
    assert linha["Data_Preco"] == ""
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
            "Data_Preco": "22.06.2026",
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
    assert linha["Data_Preco"] == "22.06.2026"
    assert linha["Preco_Custo"] == Decimal("3.25")
    assert linha["Comp"] == Decimal("100")
