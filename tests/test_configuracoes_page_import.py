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


def test_configuracoes_page_declares_technical_areas() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert ConfiguracoesPage.TECHNICAL_AREAS == [
        "Defini\u00e7\u00f5es de Pe\u00e7as",
        "Mat\u00e9rias-Primas",
        "Materiais",
        "Ferragens",
        "Opera\u00e7\u00f5es / M\u00e1quinas",
        "Regras de Custeio",
    ]


def test_configuracoes_page_has_materias_primas_shortcut() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert hasattr(ConfiguracoesPage, "_open_materias_primas")
