"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog

from app.config.logging_config import configure_logging
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


def main() -> int:
    """Start the desktop application."""
    configure_logging()

    qt_app = QApplication(sys.argv)

    login_window = LoginWindow()
    if login_window.exec() != QDialog.DialogCode.Accepted or login_window.authenticated_user is None:
        return 0

    window = MainWindow(authenticated_user=login_window.authenticated_user)
    window.show()

    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
