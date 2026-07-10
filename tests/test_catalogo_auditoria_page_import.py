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


def test_catalogo_auditoria_esta_ligada_as_configuracoes() -> None:
    from app.ui.main_window import MainWindow
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    signature = inspect.signature(ConfiguracoesPage.__init__)
    assert "on_open_catalogo_auditoria" in signature.parameters
    assert "catalogo_auditoria" in inspect.getsource(MainWindow.__init__)
