"""Import checks for the Pesquisa IA page."""

from __future__ import annotations

import inspect
from datetime import datetime
from types import SimpleNamespace


def test_pesquisa_ia_page_imports() -> None:
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage

    assert PesquisaIAPage is not None


def test_pesquisa_ia_page_headers_por_fonte() -> None:
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage

    assert PesquisaIAPage.V3_HEADERS == [
        "Ref LE",
        "Ref Forn",
        "Descri\u00e7\u00e3o",
        "Pre\u00e7o tab",
        "Mrg (+)",
        "Desc (-)",
        "P. L\u00edq",
        "Und",
        "Orla 0.4",
        "Orla 1.0",
        "Comp",
        "Larg",
        "Esp",
        "Fabricante",
        "Atualizado",
    ]
    assert PesquisaIAPage.PHC_HEADERS == [
        "Ref",
        "Ref Forn",
        "Descri\u00e7\u00e3o",
        "Fam\u00edlia",
        "Fornecedor",
        "Pre\u00e7o Custo",
        "\u00dalt. Venda",
        "Und",
        "Stock",
        "Comp",
        "Larg",
        "Esp",
        "Data pre\u00e7o",
        "Obs",
    ]


def test_pesquisa_ia_page_usa_tabelas_separadas_e_padroes_visuais() -> None:
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage, _nova_tabela

    init_source = inspect.getsource(PesquisaIAPage.__init__)
    carregar_v3_source = inspect.getsource(PesquisaIAPage.carregar_v3)
    carregar_phc_source = inspect.getsource(PesquisaIAPage.carregar_phc)
    pesquisa_source = inspect.getsource(PesquisaIAPage.aplicar_pesquisa)
    preencher_v3_source = inspect.getsource(PesquisaIAPage._preencher_v3)
    preencher_phc_source = inspect.getsource(PesquisaIAPage._preencher_phc)
    preencher_refs_source = inspect.getsource(PesquisaIAPage._preencher_referencias)
    resposta_source = inspect.getsource(PesquisaIAPage.gerar_resposta)
    nova_tabela_source = inspect.getsource(_nova_tabela)

    assert "BarraCabecalho" in init_source
    assert "CampoPesquisa" in init_source
    assert "self.v3_table" in init_source
    assert "self.phc_table" in init_source
    assert "self.referencias_table" in init_source
    assert "pesquisa_ia_v3" in init_source
    assert "pesquisa_ia_phc" in init_source
    assert "pesquisa_ia_referencias" in init_source
    assert "Mat\\u00e9rias-primas V3" in init_source
    assert "Artigos PHC" in init_source
    assert "QHeaderView.ResizeMode.Interactive" in nova_tabela_source
    assert "ligar_persistencia_larguras" in nova_tabela_source
    assert "DefMateriaPrimaService" in carregar_v3_source
    assert "query_phc_materiais" in carregar_phc_source
    assert "_v3_corresponde" in pesquisa_source
    assert "_phc_corresponde" in pesquisa_source
    assert "_ref_corresponde" in pesquisa_source
    assert "self._preencher_v3" in pesquisa_source
    assert "self._preencher_phc" in pesquisa_source
    assert "tema.cor_zebra(row_index)" in inspect.getsource(
        PesquisaIAPage._escrever_linha
    )
    assert "format_currency(materia.preco_tabela)" in preencher_v3_source
    assert "materia.coresp_orla_0_4" in preencher_v3_source
    assert "format_currency(linha.get(\"Preco_Ultimo\"))" in preencher_phc_source
    assert "linha.get(\"Data_Preco\")" in preencher_phc_source
    assert "referencia.precos.get" in preencher_refs_source
    assert "ARTIGOS (mat\\u00e9rias-primas V3/PHC)" in resposta_source
    assert "self._v3_filtrados[:8]" in resposta_source
    assert "self._phc_filtrados[:8]" in resposta_source
    assert "Preco_Ultimo" in resposta_source
    assert "REFER\\u00caNCIAS DE PLACAS" in resposta_source
    assert "TRECHOS DE CAT\\u00c1LOGOS" in resposta_source


def test_pesquisa_ia_resposta_e_nao_bloqueante_com_streaming() -> None:
    from app.ui.pages import pesquisa_ia_page as page_module

    gerar_source = inspect.getsource(page_module.PesquisaIAPage.gerar_resposta)
    iniciar_source = inspect.getsource(page_module.PesquisaIAPage._iniciar_geracao)
    worker_run_source = inspect.getsource(page_module._RespostaWorker.run)

    # A geracao corre fora da thread da UI...
    assert "self._iniciar_geracao(pergunta, contexto)" in gerar_source
    assert "QThread" in iniciar_source
    assert "moveToThread" in iniciar_source
    # ...e o texto chega em pedacos (streaming) por sinais.
    assert "gerar_stream" in worker_run_source
    assert "self.pedaco.emit" in worker_run_source


def test_pesquisa_ia_v3_corresponde_normaliza_e_procura_campos_proprios() -> None:
    from app.ui.pages.pesquisa_ia_page import _v3_corresponde

    materia = SimpleNamespace(
        ref_le="V3-001",
        referencia_fornecedor="FORN-55",
        descricao="Aglomerado carvalho",
        fornecedor="Armaz\u00e9ns Reis",
        coresp_orla_0_4="ORLA-04",
        coresp_orla_1_0="ORLA-10",
    )

    assert _v3_corresponde(materia, "aglomerado reis") is True
    assert _v3_corresponde(materia, "forn 55 orla") is True
    assert _v3_corresponde(materia, "dobradica") is False


def test_pesquisa_ia_phc_corresponde_normaliza_e_procura_campos_proprios() -> None:
    from app.ui.pages.pesquisa_ia_page import _phc_corresponde

    linha = {
        "Ref": "PHC-001",
        "Descricao": "Dobradi\u00e7a reta",
        "Familia_Nome": "Ferragens",
        "Fornecedor": "Blum",
        "Ref_Fornecedor": "BL-71",
    }

    assert _phc_corresponde(linha, "dobradica blum") is True
    assert _phc_corresponde(linha, "ferragens bl 71") is True
    assert _phc_corresponde(linha, "aglomerado") is False


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


def test_pesquisa_ia_data_curta_formata_datetime() -> None:
    from app.ui.pages.pesquisa_ia_page import _data_curta

    assert _data_curta(datetime(2026, 3, 26, 12, 30)) == "26-03-2026"
    assert _data_curta(None) == ""
    assert _data_curta("26.03.2026") == "26.03.2026"
