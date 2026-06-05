"""Login dialog for Martelo Orcamentos V3."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models import User
from app.services.auth_service import AuthenticationError, InactiveUserError, authenticate_user


class LoginWindow(QDialog):
    """Simple authentication dialog."""

    def __init__(self) -> None:
        super().__init__()

        self.authenticated_user: User | None = None

        self.setWindowTitle("Login - Martelo Or\u00e7amentos V3")
        self.setModal(True)
        self.setMinimumWidth(360)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.handle_login)

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #b00020;")

        self.login_button = QPushButton("Entrar")
        self.login_button.clicked.connect(self.handle_login)

        form_layout = QFormLayout()
        form_layout.addRow("Username", self.username_input)
        form_layout.addRow("Password", self.password_input)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addWidget(self.login_button)
        self.setLayout(layout)

    def handle_login(self) -> None:
        """Authenticate the user with the provided credentials."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        self.error_label.clear()

        if not username or not password:
            self.error_label.setText("Preencha username e password.")
            return

        try:
            with SessionLocal() as session:
                self.authenticated_user = authenticate_user(session, username, password)
        except InactiveUserError:
            self.password_input.clear()
            self.error_label.setText("Utilizador inativo. Contacte o administrador.")
            return
        except AuthenticationError:
            self.password_input.clear()
            self.error_label.setText("Username ou password invalidos.")
            return
        except SQLAlchemyError:
            self.password_input.clear()
            self.error_label.setText("Nao foi possivel validar o login. Tente novamente.")
            return

        self.accept()
