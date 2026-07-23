"""Administrator page for accounts and menu permissions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.db.session import SessionLocal
from app.domain.departamentos import DEPARTAMENTOS
from app.services.permission_service import MENU_PERMISSIONS
from app.services.user_admin_service import (
    create_user,
    list_managed_users,
    reset_password,
    update_user_access,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho


def _combo_departamentos(valor: str = "") -> QComboBox:
    """Combo editavel com as areas sugeridas — aceita areas novas."""
    combo = QComboBox()
    combo.setEditable(True)
    combo.addItem("")
    combo.addItems(DEPARTAMENTOS)
    combo.setCurrentText(valor)
    combo.setToolTip(
        "Área de trabalho da pessoa. Se faltar alguma, escreva-a — a lista é "
        "só uma sugestão."
    )
    return combo


class NewUserDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo utilizador")
        form = QFormLayout(self)
        self.username = QLineEdit()
        self.nome = QLineEdit()
        self.email = QLineEdit()
        self.departamento = _combo_departamentos()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username", self.username)
        form.addRow("Nome", self.nome)
        form.addRow("Email", self.email)
        form.addRow("Departamento", self.departamento)
        form.addRow("Palavra-passe", self.password)
        form.addRow("Confirmar", self.confirm)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Criar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class UserManagementPage(QWidget):
    """Manage normal accounts and their visible V3 menu areas."""

    FIXED_COLUMNS = ("Utilizador", "Nome", "Email", "Função", "Departamento", "Ativo")

    def __init__(self, on_back=None) -> None:
        super().__init__()
        self.on_back = on_back
        self.cabecalho = BarraCabecalho(
            "Utilizadores e acessos",
            [
                "O administrador pode criar contas, ativá-las ou desativá-las e "
                "definir os menus apresentados a cada utilizador."
            ],
        )
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setColumnCount(len(self.FIXED_COLUMNS) + len(MENU_PERMISSIONS))
        self.table.setHorizontalHeaderLabels(
            [*self.FIXED_COLUMNS, *MENU_PERMISSIONS.values()]
        )

        self.new_button = QPushButton("Novo utilizador")
        self.new_button.clicked.connect(self._new_user)
        self.password_button = QPushButton("Redefinir palavra-passe")
        self.password_button.clicked.connect(self._reset_password)
        self.save_button = QPushButton("Gravar acessos")
        self.save_button.clicked.connect(self._save)
        self.reload_button = QPushButton("Recarregar")
        self.reload_button.clicked.connect(self.carregar)
        self.voltar_button = QPushButton("Voltar às Configurações")
        self.voltar_button.setToolTip("Regressar ao menu Configurações.")
        self.voltar_button.clicked.connect(
            lambda: self.on_back() if self.on_back else None
        )
        self.voltar_button.setVisible(self.on_back is not None)

        buttons = QHBoxLayout()
        buttons.addWidget(self.new_button)
        buttons.addWidget(self.password_button)
        buttons.addStretch()
        buttons.addWidget(self.reload_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.voltar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("userManagementStatus")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(self.cabecalho)
        layout.addLayout(buttons)
        # Linha de acompanhamento logo abaixo dos botões, como nos outros menus.
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, 1)
        self.carregar()

    @staticmethod
    def _check_item(checked: bool, enabled: bool = True) -> QTableWidgetItem:
        item = QTableWidgetItem()
        flags = Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable
        if enabled:
            flags |= Qt.ItemFlag.ItemIsEnabled
        item.setFlags(flags)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        return item

    def carregar(self) -> None:
        try:
            with SessionLocal() as session:
                users = list_managed_users(session)
        except Exception as exc:
            self.status_label.setText("Não foi possível carregar os utilizadores.")
            QMessageBox.critical(self, "Utilizadores", f"Não foi possível carregar: {exc}")
            return
        self.table.setRowCount(len(users))
        for row_index, user in enumerate(users):
            username_item = QTableWidgetItem(user.username)
            username_item.setData(Qt.ItemDataRole.UserRole, user.id)
            username_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_index, 0, username_item)
            for column, value in enumerate((user.nome, user.email, user.role), start=1):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row_index, column, item)
            is_admin = user.role.casefold() == "admin"
            combo = _combo_departamentos(user.departamento)
            self.table.setCellWidget(row_index, 4, combo)
            self.table.setItem(row_index, 5, self._check_item(user.is_active, not is_admin))
            for offset, key in enumerate(MENU_PERMISSIONS, start=6):
                self.table.setItem(
                    row_index,
                    offset,
                    self._check_item(user.permissions[key], not is_admin),
                )
        self.table.resizeColumnsToContents()
        self.status_label.setText(
            f"{len(users)} utilizador(es). Escolha o departamento, marque os "
            "menus visíveis e clique em Gravar acessos para aplicar."
        )

    def _new_user(self) -> None:
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
                    departamento=dialog.departamento.currentText(),
                )
        except Exception as exc:
            QMessageBox.warning(self, "Novo utilizador", str(exc))
            return
        self.carregar()

    def _selected_user_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _reset_password(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            QMessageBox.information(self, "Palavra-passe", "Selecione um utilizador.")
            return
        password, accepted = QInputDialog.getText(
            self,
            "Redefinir palavra-passe",
            "Nova palavra-passe (mínimo 8 caracteres):",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return
        try:
            with SessionLocal() as session:
                reset_password(session, user_id, password)
        except Exception as exc:
            QMessageBox.warning(self, "Palavra-passe", str(exc))
            return
        QMessageBox.information(self, "Palavra-passe", "Palavra-passe atualizada.")

    def _save(self) -> None:
        try:
            with SessionLocal() as session:
                for row in range(self.table.rowCount()):
                    user_id = int(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole))
                    permissions = {
                        key: self.table.item(row, column).checkState() == Qt.CheckState.Checked
                        for column, key in enumerate(MENU_PERMISSIONS, start=6)
                    }
                    combo = self.table.cellWidget(row, 4)
                    update_user_access(
                        session,
                        user_id=user_id,
                        is_active=self.table.item(row, 5).checkState() == Qt.CheckState.Checked,
                        permissions=permissions,
                        departamento=combo.currentText() if combo is not None else None,
                    )
                session.commit()
        except Exception as exc:
            QMessageBox.critical(self, "Utilizadores", f"Não foi possível gravar: {exc}")
            return
        QMessageBox.information(self, "Utilizadores", "Acessos gravados.")
        self.carregar()
        self.status_label.setText(
            "Acessos gravados. As alterações aplicam-se no próximo login de "
            "cada utilizador."
        )
