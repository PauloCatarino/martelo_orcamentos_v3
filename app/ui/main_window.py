"""Main application window for Martelo Orcamentos V3."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models import User


class MainWindow(QMainWindow):
    """Application shell window."""

    logout_requested = Signal()

    def __init__(self, authenticated_user: User | None = None) -> None:
        super().__init__()

        self.authenticated_user = authenticated_user

        self.setWindowTitle("Martelo Or\u00e7amentos V3")
        self.resize(1100, 720)

        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel("Martelo Or\u00e7amentos V3")
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        user_label = QLabel(self._format_user_info())
        user_label.setObjectName("authenticatedUserInfo")
        user_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        logout_button = QPushButton("Sair")
        logout_button.setObjectName("logoutButton")
        logout_button.clicked.connect(self.request_logout)

        header_layout.addWidget(title, stretch=1)
        header_layout.addWidget(user_label, stretch=1)
        header_layout.addWidget(logout_button)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        sidebar.setFixedWidth(180)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)

        for label in ("In\u00edcio", "Or\u00e7amentos", "Clientes", "Configura\u00e7\u00f5es"):
            button = QPushButton(label)
            button.setEnabled(False)
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)

        workspace = QFrame()
        workspace.setFrameShape(QFrame.Shape.StyledPanel)

        workspace_layout = QVBoxLayout()
        welcome_label = QLabel("Bem-vindo ao Martelo Or\u00e7amentos V3")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        workspace_layout.addWidget(welcome_label)
        workspace.setLayout(workspace_layout)

        content_layout.addWidget(sidebar)
        content_layout.addWidget(workspace, stretch=1)

        main_layout.addLayout(header_layout)
        main_layout.addLayout(content_layout, stretch=1)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def _format_user_info(self) -> str:
        """Return display text for the authenticated user."""
        if self.authenticated_user is None:
            return "Utilizador: n/a"

        return (
            f"{self.authenticated_user.nome}\n"
            f"@{self.authenticated_user.username} | {self.authenticated_user.role}"
        )

    def request_logout(self) -> None:
        """Emit a logout request."""
        self.logout_requested.emit()
