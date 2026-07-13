"""Verificações leves da página de configuração iMos."""

from __future__ import annotations

import inspect


def test_pagina_imos_importa_e_expoe_acoes() -> None:
    from app.ui.pages.imos_ligacao_page import ImosLigacaoPage

    source = inspect.getsource(ImosLigacaoPage)
    assert "Guardar configuração" in source
    assert "Testar ligação e permissões" in source
    assert "barreira do Martelo aceita apenas SELECT" in source
    assert "Mostrar password" in source


def test_configuracoes_expoe_callback_imos() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert "on_open_imos_ligacao" in inspect.signature(ConfiguracoesPage).parameters
    assert "Ligação iMos (leitura)" in ConfiguracoesPage.TECHNICAL_AREAS
