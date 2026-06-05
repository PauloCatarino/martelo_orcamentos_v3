"""Tests for the main application window."""

from __future__ import annotations

import inspect


def test_main_window_accepts_authenticated_user_argument() -> None:
    from app.ui.main_window import MainWindow

    signature = inspect.signature(MainWindow)

    assert "authenticated_user" in signature.parameters


def test_main_window_has_def_pecas_navigation_inside_configuracoes() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)

    assert "ConfiguracoesPage" in source
    assert "DefPecasPage" in source
    assert '"pecas"' in source
    assert "pecas_button" not in source
