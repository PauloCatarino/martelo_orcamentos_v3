"""Import checks for the login window."""

from __future__ import annotations


def test_login_window_imports() -> None:
    from app.ui.login_window import LoginWindow

    assert LoginWindow is not None
