"""Regression checks for navigation back to Configurações."""

from __future__ import annotations

import inspect


def test_submenus_configuracoes_expoem_regresso_consistente():
    from app.ui.pages.caminhos_sistema_page import CaminhosSistemaPage
    from app.ui.pages.def_pecas_page import DefPecasPage
    from app.ui.pages.def_valueset_chaves_page import DefValuesetChavesPage
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage
    from app.ui.pages.imos_ligacao_page import ImosLigacaoPage
    from app.ui.pages.margens_padrao_page import MargensPadraoPage
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage
    from app.ui.pages.regras_quantidade_page import RegrasQuantidadePage

    for page in (
        CaminhosSistemaPage,
        DefPecasPage,
        DefValuesetChavesPage,
        DefValuesetModelosPage,
        ImosLigacaoPage,
        MargensPadraoPage,
        OperacoesMaquinasPage,
        RegrasQuantidadePage,
    ):
        source = inspect.getsource(page.__init__)
        assert "Voltar às Configurações" in source
        assert "on_back" in source


def test_cliente_final_usa_layout_compacto_do_botao_guardar():
    from app.ui.pages.margens_padrao_page import MargensPadraoPage

    source = inspect.getsource(MargensPadraoPage._criar_tab_cliente_final)
    assert "guardar_cliente_final_button" in source
    assert "buttons_layout = QHBoxLayout()" in source
    assert "TOOLTIP_VALOR_INICIAL" in source


def test_barras_de_pesquisa_mantem_acoes_juntas_a_esquerda():
    from app.ui.pages.clientes_page import ClientesPage
    from app.ui.pages.materias_primas_page import MateriasPrimasPage
    from app.ui.pages.pesquisa_ia_page import PesquisaIAPage

    sources = (
        inspect.getsource(ClientesPage._criar_tab_temporarios),
        inspect.getsource(ClientesPage._criar_tab_phc),
        inspect.getsource(MateriasPrimasPage.__init__),
        inspect.getsource(PesquisaIAPage.__init__),
    )
    for source in sources:
        assert "addStretch()" in source

    assert "addWidget(self.campo_pesquisa)" in sources[0]
    assert "addWidget(self.phc_campo_pesquisa)" in sources[1]
    assert "addWidget(self.campo_pesquisa)" in sources[2]
    assert "addWidget(self.campo_pesquisa)" in sources[3]
