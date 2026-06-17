"""Application entry point."""

from __future__ import annotations

import sys

# O backend Qt do matplotlib importa dateutil -> six.moves; se isso correr DEPOIS do
# PySide6 ser importado, o hook de "feature" do shiboken rebenta
# ('_SixMetaPathImporter' object has no attribute '_path'). Pré-carregar aqui, antes do
# PySide6, evita o conflito. Opcional: se o matplotlib não existir, os dashboards
# mostram apenas o aviso de fallback.
try:
    import matplotlib
    matplotlib.use("QtAgg")
    import matplotlib.dates  # noqa: F401  -- pré-carrega a cadeia dateutil/six.moves
except Exception:
    pass

from PySide6.QtWidgets import QApplication, QDialog

from app.config.logging_config import configure_logging
from app.core.session import app_session
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


def main() -> int:
    """Start the desktop application."""
    configure_logging()

    qt_app = QApplication(sys.argv)

    while True:
        login_window = LoginWindow()
        if login_window.exec() != QDialog.DialogCode.Accepted or login_window.authenticated_user is None:
            app_session.clear_current_user()
            return 0

        app_session.set_current_user(login_window.authenticated_user)

        logout_requested = False

        window = MainWindow(authenticated_user=app_session.current_user)

        def handle_logout() -> None:
            nonlocal logout_requested
            logout_requested = True
            app_session.clear_current_user()
            window.close()

        window.logout_requested.connect(handle_logout)
        window.show()

        qt_app.exec()

        if logout_requested:
            continue

        app_session.clear_current_user()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
