"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config.logging_config import configure_logging
from app.ui.main_window import MainWindow


def main() -> int:
    """Start the desktop application."""
    configure_logging()

    qt_app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

