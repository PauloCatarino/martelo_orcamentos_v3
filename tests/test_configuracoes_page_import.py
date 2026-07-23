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
    assert "on_open_imos_ligacao" in signature.parameters


def test_configuracoes_page_declares_technical_areas() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert ConfiguracoesPage.TECHNICAL_AREAS == [
        "Defini\u00e7\u00f5es de Pe\u00e7as",
        "Caminhos do Sistema",
        "Liga\u00e7\u00e3o iMos (leitura)",
        "Opera\u00e7\u00f5es / M\u00e1quinas",
        "Chaves ValueSet",
        "Modelos ValueSet",
        "Margens por Defeito",
        "Regras de Quantidade",
        "Biblioteca de Módulos",
        "Auditoria do Catálogo",
        "A Minha Biblioteca de Peças",
        "Assistente — o meu perfil",
    ]


def test_configuracoes_page_tem_tooltip_em_todas_as_areas() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert set(ConfiguracoesPage.TOOLTIP_DESCRICOES) == set(
        ConfiguracoesPage.TECHNICAL_AREAS
    )
    assert all(ConfiguracoesPage.TOOLTIP_DESCRICOES.values())


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


def test_configuracoes_page_nao_tem_materias_primas_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    init_source = inspect.getsource(ConfiguracoesPage.__init__)

    assert not hasattr(ConfiguracoesPage, "_open_materias_primas")
    assert "materias_primas_button" not in init_source
    assert "Mat\\u00e9rias-Primas" not in init_source
    assert 'QPushButton("Materiais")' not in init_source
    assert 'QPushButton("Ferragens")' not in init_source
    assert 'QPushButton("Regras de Custeio")' not in init_source


def test_configuracoes_page_has_caminhos_sistema_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert hasattr(ConfiguracoesPage, "_open_caminhos_sistema")


def test_configuracoes_page_has_operacoes_maquinas_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    signature = inspect.signature(ConfiguracoesPage)

    assert "on_open_operacoes_maquinas" in signature.parameters
    assert hasattr(ConfiguracoesPage, "_open_operacoes_maquinas")
