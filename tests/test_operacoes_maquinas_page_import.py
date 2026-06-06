"""Import checks for the Operacoes / Maquinas page."""

from __future__ import annotations

import inspect


def test_operacoes_maquinas_page_imports() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    assert OperacoesMaquinasPage is not None


def test_operacoes_maquinas_page_registered_in_pages() -> None:
    from app.ui.pages import OperacoesMaquinasPage

    assert OperacoesMaquinasPage is not None


def test_operacoes_headers() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    assert OperacoesMaquinasPage.OPERACOES_HEADERS == [
        "Código",
        "Nome",
        "Tipo",
        "Unidade cálculo",
        "Máquina",
        "Tempo base",
        "Tempo setup",
        "Custo/hora",
        "Custo mínimo",
        "Ativo",
    ]


def test_maquinas_headers() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    assert OperacoesMaquinasPage.MAQUINAS_HEADERS == [
        "Código",
        "Nome",
        "Tipo",
        "Custo/hora",
        "Ativo",
    ]


def test_operacoes_maquinas_page_loads_on_init() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    source_names = OperacoesMaquinasPage.__init__.__code__.co_names

    assert "carregar" in source_names
    assert "QTabWidget" in source_names


def test_operacoes_maquinas_page_uses_services() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    source = inspect.getsource(OperacoesMaquinasPage.carregar)

    assert "DefOperacaoService" in source
    assert "DefMaquinaService" in source
    assert "listar_operacoes" in source
    assert "listar_maquinas" in source


def test_operacoes_maquinas_page_has_expected_methods() -> None:
    from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

    for method in ("carregar", "_preencher_operacoes", "_preencher_maquinas"):
        assert hasattr(OperacoesMaquinasPage, method)
