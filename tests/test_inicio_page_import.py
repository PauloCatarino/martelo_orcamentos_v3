from __future__ import annotations

import inspect


def test_inicio_page_importa_e_usa_dados_reais() -> None:
    from app.ui.pages.inicio_page import InicioPage

    source = inspect.getsource(InicioPage.carregar)
    assert "OrcamentoService" in source
    assert "calcular_dashboard_orcamentos" in source
    assert "calcular_producao" in source


def test_main_window_usa_inicio_page() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)
    assert "InicioPage" in source
    assert 'self._add_page("inicio", self.inicio_page)' in source
    assert 'self._add_page("orcamentos_dashboard", self.orcamentos_dashboard_page)' in source


def test_inicio_page_pode_ser_dashboard_dedicado_sem_producao() -> None:
    from app.ui.pages.inicio_page import InicioPage

    signature = inspect.signature(InicioPage)
    assert "titulo" in signature.parameters
    assert "incluir_producao" in signature.parameters


def test_inicio_tem_filtros_dez_cartoes_e_tabela_compacta() -> None:
    from app.ui.pages.inicio_page import InicioPage

    init = inspect.getsource(InicioPage.__init__)
    carregar = inspect.getsource(InicioPage.carregar)
    preencher = inspect.getsource(InicioPage._preencher_recentes)
    for nome in ("pesquisa", "estado_combo", "cliente_combo", "utilizador_combo",
                 "periodo_combo", "relogio_label"):
        assert nome in init
    for cartao in ("desenho", "finalizadas", "valor_producao", "sem_preco_producao"):
        assert cartao in init
    assert "QTableWidget(0, 10)" in init
    assert "ref_cliente" in preencher
    assert "enc_phc" in preencher
    assert "utilizador" in preencher
    assert "cliente=none if cliente_producao" in carregar.casefold()
    assert "utilizador=none if utilizador_producao" in carregar.casefold()


def test_inicio_separa_avisos_orcamentos_e_producao() -> None:
    from app.ui.pages.inicio_page import InicioPage

    init = inspect.getsource(InicioPage.__init__)
    assert 'QGroupBox("Orçamentos")' in init
    assert 'QGroupBox("Produção")' in init
    assert hasattr(InicioPage, "_preencher_avisos_producao")


def test_inicio_usa_estilo_comum_de_orcamentos() -> None:
    from app.ui.pages.inicio_page import InicioPage

    init = inspect.getsource(InicioPage.__init__)
    preencher = inspect.getsource(InicioPage._preencher_recentes)
    assert "configurar_tabela_orcamentos" in init
    assert "aplicar_estilo_linha_orcamento" in preencher


def test_inicio_integra_resumo_auditoria_custeio() -> None:
    from app.ui.pages.inicio_page import InicioPage

    carregar = inspect.getsource(InicioPage.carregar)
    assert "CusteioAuditoriaService" in carregar
    assert "auditoria_custeio.criticos" in carregar
    assert "impacto_conhecido" in carregar
