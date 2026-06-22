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

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QProxyStyle,
    QStyle,
    QStyleOptionViewItem,
)

from app.config.logging_config import configure_logging
from app.core.session import app_session
from app.ui import tema
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


class EstiloSelecaoLegivel(QProxyStyle):
    """Força texto branco legível em qualquer célula selecionada."""

    def drawControl(self, element, option, painter, widget=None) -> None:  # noqa: N802
        if (
            element == QStyle.ControlElement.CE_ItemViewItem
            and isinstance(option, QStyleOptionViewItem)
            and (option.state & QStyle.StateFlag.State_Selected)
        ):
            opcao = QStyleOptionViewItem(option)
            branco = QColor("#FFFFFF")
            opcao.palette.setColor(QPalette.ColorRole.HighlightedText, branco)
            opcao.palette.setColor(QPalette.ColorRole.Text, branco)
            super().drawControl(element, opcao, painter, widget)
            return
        super().drawControl(element, option, painter, widget)


def main() -> int:
    """Start the desktop application."""
    configure_logging()

    qt_app = QApplication(sys.argv)
    # Estilo que garante texto branco em qualquer célula selecionada (todas as tabelas).
    qt_app.setStyle(EstiloSelecaoLegivel())
    # Cor de seleção do tema via paleta, incluindo quando a tabela perde foco.
    paleta = qt_app.palette()
    realce_fundo = QColor(tema.CASTANHO_ESCURO)
    realce_texto = QColor("#FFFFFF")
    for grupo in (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled,
    ):
        paleta.setColor(grupo, QPalette.ColorRole.Highlight, realce_fundo)
        paleta.setColor(grupo, QPalette.ColorRole.HighlightedText, realce_texto)
    qt_app.setPalette(paleta)
    # Realce transversal do separador selecionado (R2.11).
    qt_app.setStyleSheet(tema.ESTILO_ABAS)

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
        window.showMaximized()

        qt_app.exec()

        if logout_requested:
            continue

        app_session.clear_current_user()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
