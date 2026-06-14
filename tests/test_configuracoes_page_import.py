"""Import checks for the Configuracoes page."""

from __future__ import annotations

import inspect


def test_configuracoes_page_imports() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert ConfiguracoesPage is not None


def test_configuracoes_page_accepts_def_pecas_callback() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    signature = inspect.signature(ConfiguracoesPage)

    assert "on_open_def_pecas" in signature.parameters
    assert "on_open_materias_primas" in signature.parameters
    assert "on_open_caminhos_sistema" in signature.parameters


def test_configuracoes_page_declares_technical_areas() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert ConfiguracoesPage.TECHNICAL_AREAS == [
        "Defini\u00e7\u00f5es de Pe\u00e7as",
        "Mat\u00e9rias-Primas",
        "Caminhos do Sistema",
        "Materiais",
        "Ferragens",
        "Opera\u00e7\u00f5es / M\u00e1quinas",
        "Chaves ValueSet",
        "Modelos ValueSet",
        "Margens por Defeito",
        "Regras de Quantidade",
        "Biblioteca de Módulos",
        "Regras de Custeio",
    ]


def test_configuracoes_page_has_biblioteca_modulos_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    signature = inspect.signature(ConfiguracoesPage)

    assert "on_open_biblioteca_modulos" in signature.parameters
    assert hasattr(ConfiguracoesPage, "_open_biblioteca_modulos")


def test_configuracoes_page_has_regras_quantidade_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    signature = inspect.signature(ConfiguracoesPage)

    assert "on_open_regras_quantidade" in signature.parameters
    assert hasattr(ConfiguracoesPage, "_open_regras_quantidade")


def test_configuracoes_page_has_margens_padrao_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    signature = inspect.signature(ConfiguracoesPage)

    assert "on_open_margens_padrao" in signature.parameters
    assert hasattr(ConfiguracoesPage, "_open_margens_padrao")


def test_configuracoes_page_has_valueset_chaves_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    signature = inspect.signature(ConfiguracoesPage)

    assert "on_open_valueset_chaves" in signature.parameters
    assert hasattr(ConfiguracoesPage, "_open_valueset_chaves")


def test_configuracoes_page_has_valueset_modelos_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    signature = inspect.signature(ConfiguracoesPage)

    assert "on_open_valueset_modelos" in signature.parameters
    assert hasattr(ConfiguracoesPage, "_open_valueset_modelos")


def test_configuracoes_page_has_materias_primas_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert hasattr(ConfiguracoesPage, "_open_materias_primas")


def test_configuracoes_page_has_caminhos_sistema_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert hasattr(ConfiguracoesPage, "_open_caminhos_sistema")


def test_configuracoes_page_has_operacoes_maquinas_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    signature = inspect.signature(ConfiguracoesPage)

    assert "on_open_operacoes_maquinas" in signature.parameters
    assert hasattr(ConfiguracoesPage, "_open_operacoes_maquinas")
