"""Tests for the main application window."""

from __future__ import annotations

import inspect


def test_main_window_accepts_authenticated_user_argument() -> None:
    from app.ui.main_window import MainWindow

    signature = inspect.signature(MainWindow)

    assert "authenticated_user" in signature.parameters


def test_main_window_has_def_pecas_page_navigation() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)

    assert "DefPecasPage" in source
    assert '"pecas"' in source
