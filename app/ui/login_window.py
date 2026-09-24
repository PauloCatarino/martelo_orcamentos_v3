"""Login dialog for Martelo Orcamentos V3."""

from __future__ import annotations
from app.ui import tema

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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

from app.core import diario_bordo, login_memorizado
from app.db.session import (
    BaseIndisponivel,
    CredenciaisInvalidas,
    SessionLocal,
    ligar,
)
from app.models import User
from app.services.auth_service import (
    AuthenticationError,
    InactiveUserError,
    carregar_perfil,
)
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
        self.username_input.setToolTip("O seu nome de utilizador do Martelo.")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setToolTip("A sua palavra-passe do Martelo.")
        self.password_input.returnPressed.connect(self.handle_login)

        self.memorizar_checkbox = QCheckBox("Memorizar neste computador")
        self.memorizar_checkbox.setToolTip(
            "Da próxima vez que abrir o Martelo neste PC, entra sozinho com esta "
            "conta, sem pedir o login.\n\n"
            "A palavra-passe fica guardada no Gestor de Credenciais do Windows, "
            "cifrada pelo próprio Windows e só para este PC.\n"
            "Quem usar este PC com a sua sessão do Windows entra no Martelo como "
            "você — bloqueie o PC (Windows + L) quando sair.\n\n"
            "Para deixar de memorizar: tire este visto e entre de novo.\n"
            "Contas de administrador nunca ficam memorizadas."
        )

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")

        self.login_button = QPushButton("Entrar")
        self.login_button.setToolTip("Entrar no Martelo com este utilizador.")
        self.login_button.clicked.connect(self.handle_login)

        self.create_user_button = QPushButton("Criar utilizador...")
        self.create_user_button.setToolTip(
            "Criar uma conta nova (pede a autorização de um administrador)."
        )
        self.create_user_button.clicked.connect(self.open_create_user)

        self.manage_users_button = QPushButton("Gerir utilizadores (admin)...")
        self.manage_users_button.setToolTip(
            "Contas e acessos aos menus (pede a autorização de um administrador)."
        )
        self.manage_users_button.clicked.connect(self.open_manage_users)

        form_layout = QFormLayout()
        form_layout.addRow("Username", self.username_input)
        form_layout.addRow("Password", self.password_input)

        # Quem está memorizado neste PC já vem escrito: depois de uma mudança de
        # utilizador basta a palavra-passe (ou escrever outro nome).
        self._memorizado = login_memorizado.ler()
        if self._memorizado is not None:
            self.username_input.setText(self._memorizado.username)
            self.memorizar_checkbox.setChecked(True)
            self.password_input.setFocus()
        self.username_input.textEdited.connect(self._username_mudou)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.memorizar_checkbox)
        layout.addWidget(self.error_label)
        layout.addWidget(self.login_button)

        layout.addWidget(self.create_user_button)
        layout.addWidget(self.manage_users_button)
        self.setLayout(layout)

    def _username_mudou(self, texto: str) -> None:
        """Outro nome que não o memorizado → o visto sai sozinho.

        É o caso do administrador a entrar no PC de um colega: sem isto, o
        visto que vinha marcado para o colega memorizava a conta de quem entrou
        por cima da dele.
        """
        if self._memorizado is None:
            return
        self.memorizar_checkbox.setChecked(
            texto.strip().casefold() == self._memorizado.username.casefold()
        )

    def entrar_memorizado(self) -> bool:
        """Entrar sem mostrar a janela, com o login memorizado neste PC.

        Devolve ``False`` se não houver login memorizado ou se ele já não servir;
        nesse caso a janela fica pronta, com a explicação, para entrar à mão.
        """
        memorizado = self._memorizado
        if memorizado is None:
            return False

        try:
            ligar(memorizado.username, memorizado.password)
        except CredenciaisInvalidas:
            # A palavra-passe foi mudada (por ele noutro PC, ou pelo admin).
            login_memorizado.esquecer()
            self.error_label.setText(
                "A palavra-passe memorizada neste computador deixou de servir "
                "(foi mudada?). Escreva-a de novo — fica memorizada outra vez."
            )
            diario_bordo.registar_aviso(
                "Login memorizado", "A palavra-passe memorizada foi recusada; esquecida."
            )
            return False
        except BaseIndisponivel as exc:
            # A base não respondeu: a memória continua boa, não se mexe nela.
            self.error_label.setText(str(exc))
            return False

        try:
            with SessionLocal() as session:
                self.authenticated_user = carregar_perfil(session, memorizado.username)
        except (AuthenticationError, InactiveUserError, SQLAlchemyError) as exc:
            if isinstance(exc, InactiveUserError):
                login_memorizado.esquecer()
            self.authenticated_user = None
            self.error_label.setText(
                "Não foi possível entrar com o login memorizado neste computador. "
                "Entre à mão."
            )
            return False

        if is_admin(self.authenticated_user):
            # Nunca se grava um admin; se lá estiver, foi por fora — não entra.
            login_memorizado.esquecer()
            self.authenticated_user = None
            return False
        return True

    def _atualizar_memoria(self, username: str, password: str) -> None:
        """Depois de entrar à mão: memorizar, esquecer, ou não mexer."""
        if not self.memorizar_checkbox.isChecked():
            # Só se esquece o próprio: o admin a entrar no PC de um colega não
            # apaga o login memorizado do colega.
            if login_memorizado.e_de(username):
                login_memorizado.esquecer()
            return

        if is_admin(self.authenticated_user):
            QMessageBox.information(
                self,
                "Memorizar neste computador",
                "As contas de administrador não ficam memorizadas: quem se "
                "sentasse neste PC entrava com poderes de administrador.\n\n"
                "Entrou na mesma. Para o Martelo entrar sozinho, memorize a sua "
                "conta de utilizador normal.",
            )
            return

        login_memorizado.gravar(username, password)

    def _authenticate_admin(self) -> bool:
        """Abre a ligação com uma conta de administrador.

        A partir daqui a app trabalha com essa ligação — é ela que dá os
        privilégios para criar utilizadores e mexer nos acessos. Se depois
        alguém entrar normalmente, o ``ligar`` do login substitui-a.
        """
        credentials = AdminCredentialsDialog(self)
        if credentials.exec() != QDialog.DialogCode.Accepted:
            return False

        username = credentials.username.text().strip()
        try:
            ligar(username, credentials.password.text())
        except CredenciaisInvalidas:
            QMessageBox.warning(self, "Autorização", "Utilizador ou password inválidos.")
            return False
        except BaseIndisponivel as exc:
            QMessageBox.critical(self, "Autorização", str(exc))
            return False

        try:
            with SessionLocal() as session:
                if not is_admin(carregar_perfil(session, username)):
                    raise AuthenticationError(
                        "Apenas um administrador pode executar esta operação."
                    )
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
        """Entra na app abrindo a ligação à base com as credenciais da pessoa.

        Quem valida o utilizador e a password é o próprio MySQL: cada um tem a
        sua conta. Se a ligação abre, entrou — só falta ir buscar o perfil.
        """
        username = self.username_input.text().strip()
        password = self.password_input.text()

        self.error_label.clear()

        if not username or not password:
            self.error_label.setText("Preencha username e password.")
            return

        try:
            ligar(username, password)
        except CredenciaisInvalidas:
            self.password_input.clear()
            self.error_label.setText("Username ou password invalidos.")
            return
        except BaseIndisponivel as exc:
            self.password_input.clear()
            self.error_label.setText(str(exc))
            return

        try:
            with SessionLocal() as session:
                self.authenticated_user = carregar_perfil(session, username)
        except InactiveUserError:
            self.password_input.clear()
            self.error_label.setText("Utilizador inativo. Contacte o administrador.")
            return
        except AuthenticationError as exc:
            self.password_input.clear()
            self.error_label.setText(str(exc))
            return
        except SQLAlchemyError:
            self.password_input.clear()
            self.error_label.setText("Nao foi possivel validar o login. Tente novamente.")
            return

        self._atualizar_memoria(username, password)
        self.accept()
