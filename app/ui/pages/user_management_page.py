"""Administrator page for accounts and menu permissions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.db.session import SessionLocal
from app.domain.departamentos import DEPARTAMENTOS
from app.services.permission_service import (
    DESCRICOES_ACESSOS,
    PERMISSOES_EDITAVEIS,
    nasce_ligado,
)
from app.services.user_admin_service import (
    create_user,
    list_managed_users,
    reset_password,
    update_user_access,
)
from app.services.mysql_contas_service import MINIMO_PASSWORD
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.combo_sem_scroll import ComboSemScroll
from app.ui.icones import icone


def dica_acesso(chave: str) -> str:
    """Texto da dica do título da coluna: o mesmo que está no quadro."""
    descricao = DESCRICOES_ACESSOS[chave]
    conta_nova = "vem ligado" if nasce_ligado(chave) else "vem desligado"
    return (
        f"{descricao.grupo} — {PERMISSOES_EDITAVEIS[chave]}\n\n"
        f"{descricao.o_que_faz}\n\n"
        f"Para quem: {descricao.para_quem}\n"
        f"Numa conta nova: {conta_nova}."
    )


def _combo_departamentos(valor: str = "") -> QComboBox:
    """Combo editavel com as areas sugeridas — aceita areas novas."""
    combo = ComboSemScroll()
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
        self.password.setPlaceholderText(f"mínimo {MINIMO_PASSWORD} caracteres")
        self.password.setToolTip(
            f"Palavra-passe da pessoa: pelo menos {MINIMO_PASSWORD} caracteres, "
            "como as contas que vieram do Martelo V2."
        )
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm.setToolTip("Escreva outra vez a mesma palavra-passe.")
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
                "definir os menus apresentados a cada utilizador.",
                "Não sabe o que é um acesso? Passe o rato pelo título da coluna "
                "ou clique na coluna: o quadro «O que é cada acesso» explica-o.",
            ],
        )
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setColumnCount(len(self.FIXED_COLUMNS) + len(PERMISSOES_EDITAVEIS))
        self.table.setHorizontalHeaderLabels(list(self.FIXED_COLUMNS))
        for coluna, chave in enumerate(PERMISSOES_EDITAVEIS, start=len(self.FIXED_COLUMNS)):
            titulo = QTableWidgetItem(DESCRICOES_ACESSOS[chave].titulo_curto)
            titulo.setToolTip(dica_acesso(chave))
            self.table.setHorizontalHeaderItem(coluna, titulo)
        self.table.currentCellChanged.connect(
            lambda _linha, coluna, *_: self._mostrar_descricao(coluna)
        )
        self.table.horizontalHeader().sectionClicked.connect(self._mostrar_descricao)

        self.descricoes = self._criar_quadro_descricoes()
        caixa_descricoes = QGroupBox("O que é cada acesso")
        caixa_descricoes.setToolTip(
            "Explicação de cada coluna da grelha de cima. Clique numa coluna da "
            "grelha para a encontrar aqui."
        )
        caixa_layout = QVBoxLayout(caixa_descricoes)
        caixa_layout.setContentsMargins(8, 8, 8, 8)
        caixa_layout.addWidget(self.descricoes)
        self.divisor = QSplitter(Qt.Orientation.Vertical)
        self.divisor.setChildrenCollapsible(False)
        self.divisor.addWidget(self.table)
        self.divisor.addWidget(caixa_descricoes)
        self.divisor.setStretchFactor(0, 1)
        self.divisor.setStretchFactor(1, 1)

        self.new_button = QPushButton("Novo utilizador")
        self.new_button.setToolTip("Criar uma conta nova (nasce como utilizador normal).")
        self.new_button.clicked.connect(self._new_user)
        self.password_button = QPushButton("Redefinir palavra-passe")
        self.password_button.setToolTip(
            "Repor a palavra-passe do utilizador selecionado (administrador)."
        )
        self.password_button.clicked.connect(self._reset_password)
        # A própria palavra-passe muda-se no nome do utilizador, lá em cima:
        # esta página é só do administrador, e cada um tem de conseguir mudar
        # a sua sem depender dele.
        self.save_button = QPushButton("Gravar acessos")
        self.save_button.setToolTip(
            "Gravar os vistos e departamentos de todas as linhas. Cada pessoa "
            "vê as alterações no próximo login."
        )
        self.save_button.clicked.connect(self._save)
        self.reload_button = QPushButton("Recarregar")
        self.reload_button.setToolTip("Voltar a ler da base de dados, descartando o que não foi gravado.")
        self.reload_button.clicked.connect(self.carregar)
        self.voltar_button = QPushButton("Voltar às Configurações")
        self.voltar_button.setIcon(icone("acao_voltar"))
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
        layout.addWidget(self.divisor, 1)
        self.carregar()

    COLUNAS_DESCRICAO = ("Grupo", "Acesso", "O que dá", "Para quem", "Conta nova")

    def _criar_quadro_descricoes(self) -> QTableWidget:
        quadro = QTableWidget(len(DESCRICOES_ACESSOS), len(self.COLUNAS_DESCRICAO))
        quadro.setHorizontalHeaderLabels(list(self.COLUNAS_DESCRICAO))
        quadro.setObjectName("quadroDescricoesAcessos")
        quadro.setAlternatingRowColors(True)
        quadro.setWordWrap(True)
        quadro.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        quadro.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        quadro.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        quadro.verticalHeader().setVisible(False)
        for linha, (chave, descricao) in enumerate(DESCRICOES_ACESSOS.items()):
            valores = (
                descricao.grupo,
                PERMISSOES_EDITAVEIS[chave],
                descricao.o_que_faz,
                descricao.para_quem,
                "Ligado" if nasce_ligado(chave) else "Desligado",
            )
            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setData(Qt.ItemDataRole.UserRole, chave)
                item.setToolTip(dica_acesso(chave))
                quadro.setItem(linha, coluna, item)
        cabecalho = quadro.horizontalHeader()
        for coluna in (0, 1, 3, 4):
            cabecalho.setSectionResizeMode(coluna, QHeaderView.ResizeMode.Interactive)
        cabecalho.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        quadro.setColumnWidth(0, 170)
        quadro.setColumnWidth(1, 250)
        quadro.setColumnWidth(3, 230)
        quadro.setColumnWidth(4, 90)
        # A altura das linhas depende da largura da coluna «O que dá», que só
        # se conhece com a janela aberta: recalcula-se sempre que ela muda.
        cabecalho.sectionResized.connect(lambda *_: quadro.resizeRowsToContents())
        return quadro

    def showEvent(self, event) -> None:  # noqa: N802 - nome do Qt
        super().showEvent(event)
        self.descricoes.resizeRowsToContents()

    def _mostrar_descricao(self, coluna: int) -> None:
        """Clicar numa coluna de acesso da grelha salta para a explicação."""
        indice = coluna - len(self.FIXED_COLUMNS)
        if indice < 0 or indice >= len(PERMISSOES_EDITAVEIS):
            return
        chave = list(PERMISSOES_EDITAVEIS)[indice]
        linha = list(DESCRICOES_ACESSOS).index(chave)
        self.descricoes.selectRow(linha)
        self.descricoes.scrollToItem(self.descricoes.item(linha, 0))
        self.status_label.setText(
            f"{PERMISSOES_EDITAVEIS[chave]}: {DESCRICOES_ACESSOS[chave].o_que_faz}"
        )

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
            for offset, key in enumerate(PERMISSOES_EDITAVEIS, start=6):
                self.table.setItem(
                    row_index,
                    offset,
                    self._check_item(user.permissions[key], not is_admin),
                )
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.descricoes.resizeRowsToContents()
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
            f"Nova palavra-passe (mínimo {MINIMO_PASSWORD} caracteres):",
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
                        for column, key in enumerate(PERMISSOES_EDITAVEIS, start=6)
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
