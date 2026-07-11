"""Smoke tests for the read-only catalog audit page and navigation."""

import inspect


def test_catalogo_auditoria_page_contract() -> None:
    from app.ui.pages.catalogo_auditoria_page import CatalogoAuditoriaPage

    assert CatalogoAuditoriaPage.TABLE_HEADERS == [
        "Severidade",
        "Área",
        "Entidade",
        "Código",
        "Problema encontrado",
        "Consequência possível",
        "Sugestão",
        "Teste",
    ]
    source = inspect.getsource(CatalogoAuditoriaPage)
    assert "CatalogoAuditoriaService" in source
    assert "Todas as severidades" in source
    assert "nenhuma alteração foi feita" in source
    assert "Atualizar análise" in source
    assert "Resolver com supervisão" in source
    assert "Abrir configuração" in source
    assert hasattr(CatalogoAuditoriaPage, "resolver_selecionado")
    assert hasattr(CatalogoAuditoriaPage, "abrir_configuracao")


def test_catalogo_auditoria_esta_ligada_as_configuracoes() -> None:
    from app.ui.main_window import MainWindow
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    signature = inspect.signature(ConfiguracoesPage.__init__)
    assert "on_open_catalogo_auditoria" in signature.parameters
    assert "catalogo_auditoria" in inspect.getsource(MainWindow.__init__)
    assert hasattr(MainWindow, "_open_catalogo_auditoria_item")


def test_paginas_tecnicas_suportam_abertura_direta() -> None:
    from app.ui.pages.biblioteca_modulos_page import BibliotecaModulosPage
    from app.ui.pages.def_pecas_page import DefPecasPage
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage
    from app.ui.pages.regras_quantidade_page import RegrasQuantidadePage

    assert hasattr(DefPecasPage, "abrir_peca_por_id")
    assert hasattr(OperacoesMaquinasPage, "abrir_operacao_por_id")
    assert hasattr(RegrasQuantidadePage, "selecionar_regra_por_id")
    assert hasattr(DefValuesetModelosPage, "abrir_modelo_por_id")
    assert hasattr(BibliotecaModulosPage, "selecionar_modulo_por_id")
