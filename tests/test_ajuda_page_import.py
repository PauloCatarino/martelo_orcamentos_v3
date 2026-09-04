"""A Ajuda continua a ser um menu, e o atalho ao guia deixou de existir."""

from __future__ import annotations

import inspect


def test_main_window_regista_a_pagina_de_ajuda() -> None:
    from app.ui.main_window import MainWindow

    main_source = inspect.getsource(MainWindow)

    assert '"ajuda": "menu.ajuda"' in main_source
    assert 'self._add_page("ajuda", self.ajuda_page)' in main_source


def test_o_atalho_ao_guia_desapareceu() -> None:
    """Foi retirado com o guia narrado (2026-09-04)."""
    from app.ui.main_window import MainWindow
    from app.ui.pages.orcamentos_page import OrcamentosPage

    assert not hasattr(MainWindow, "abrir_guia_ajuda")

    orcamentos_source = inspect.getsource(OrcamentosPage)
    assert "help_create_button" not in orcamentos_source
    assert "_abrir_ajuda_criar_orcamento" not in orcamentos_source
