"""Confirma as ligações do Centro de Ajuda à navegação da aplicação."""

from __future__ import annotations

import inspect


def test_main_window_regista_ajuda_e_atalho_contextual() -> None:
    from app.ui.main_window import MainWindow
    from app.ui.pages.orcamentos_page import OrcamentosPage

    main_source = inspect.getsource(MainWindow)
    orcamentos_source = inspect.getsource(OrcamentosPage)

    assert '"ajuda": "menu.ajuda"' in main_source
    assert 'self._add_page("ajuda", self.ajuda_page)' in main_source
    assert hasattr(MainWindow, "abrir_guia_ajuda")
    assert "help_create_button" in orcamentos_source
    assert "_abrir_ajuda_criar_orcamento" in orcamentos_source
