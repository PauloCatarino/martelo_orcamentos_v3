"""Login dialog for Martelo Orcamentos V3."""

from __future__ import annotations
from app.ui import tema

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models import User
from app.services.auth_service import AuthenticationError, InactiveUserError, authenticate_user
from app.services.permission_service import is_admin
from app.services.user_admin_service import create_user
from app.ui.pages.user_management_page import NewUserDialog, UserManagementPage


class AdminCredentialsDialog(QDialog):
    """Ask for administrator credentials before pre-login account actions."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Autorização de administrador")
        form = QFormLayout(self)
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Utilizador admin", self.username)
        form.addRow("Palavra-passe admin", self.password)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


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
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")

        self.login_button = QPushButton("Entrar")
        self.login_button.clicked.connect(self.handle_login)

        self.create_user_button = QPushButton("Criar utilizador...")
        self.create_user_button.clicked.connect(self.open_create_user)

        self.manage_users_button = QPushButton("Gerir utilizadores (admin)...")
        self.manage_users_button.clicked.connect(self.open_manage_users)

        form_layout = QFormLayout()
        form_layout.addRow("Username", self.username_input)
        form_layout.addRow("Password", self.password_input)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addWidget(self.login_button)

        layout.addWidget(self.create_user_button)
        layout.addWidget(self.manage_users_button)
        self.setLayout(layout)

    def _authenticate_admin(self) -> bool:
        """Validate an administrator without changing the login dialog state."""
        credentials = AdminCredentialsDialog(self)
        if credentials.exec() != QDialog.DialogCode.Accepted:
            return False
        try:
            with SessionLocal() as session:
                user = authenticate_user(
                    session,
                    credentials.username.text().strip(),
                    credentials.password.text(),
                )
                if not is_admin(user):
                    raise AuthenticationError("Apenas um administrador pode executar esta operação.")
        except (AuthenticationError, InactiveUserError) as exc:
            QMessageBox.warning(self, "Autorização", str(exc))
            return False
        except SQLAlchemyError:
            QMessageBox.critical(self, "Autorização", "Não foi possível validar o administrador.")
            return False
        return True

    def open_create_user(self) -> None:
        """Create a normal account before the first login."""
        if not self._authenticate_admin():
            return
        dialog = NewUserDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.password.text() != dialog.confirm.text():
            QMessageBox.warning(self, "Novo utilizador", "As palavras-passe não coincidem.")
            return
        try:
            with SessionLocal() as session:
                create_user(
                    session,
                    username=dialog.username.text(),
                    nome=dialog.nome.text(),
                    email=dialog.email.text(),
                    password=dialog.password.text(),
                )
        except Exception as exc:
            QMessageBox.warning(self, "Novo utilizador", str(exc))
            return
        QMessageBox.information(self, "Novo utilizador", "Utilizador criado com sucesso.")

    def open_manage_users(self) -> None:
        """Open the full account and menu-permission manager before login."""
        if not self._authenticate_admin():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Gerir utilizadores - Martelo Orçamentos V3")
        dialog.resize(1100, 600)
        layout = QVBoxLayout(dialog)
        layout.addWidget(UserManagementPage())
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

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
