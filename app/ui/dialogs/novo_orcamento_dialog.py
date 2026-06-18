"""Dialog for creating a simple Orcamento."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.margens_padrao_types import (
    AMBITO_CLIENTE,
    AMBITO_STANDARD,
    AMBITO_UTILIZADOR,
)
from app.repositories.user_repository import UserRepository
from app.services.def_margem_padrao_service import DefMargemPadraoService


@dataclass(frozen=True)
class NovoOrcamentoDialogData:
    """Data collected by the new budget dialog."""

    nome_cliente: str
    email_cliente: str | None
    telefone_cliente: str | None
    obra: str
    descricao: str | None
    localizacao: str | None
    ref_cliente: str | None
    enc_phc: str | None = None
    info_1: str | None = None
    info_2: str | None = None
    margens_escolha: str = AMBITO_STANDARD
    utilizador_id: int | None = None


class NovoOrcamentoDialog(QDialog):
    """Simple modal dialog for creating a budget."""

    MARGENS_TOOLTIP = (
        "Conjunto de margens copiado para o novo orçamento como valor "
        "inicial; dentro do orçamento o utilizador altera livremente. "
        "'Do cliente' fica disponível quando o cliente indicado tem margens "
        "próprias; 'Do utilizador' quando o utilizador autenticado as tem."
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Novo Orçamento")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.nome_cliente_input = QLineEdit()
        self.email_cliente_input = QLineEdit()
        self.telefone_cliente_input = QLineEdit()
        self.obra_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(90)
        self.localizacao_input = QLineEdit()
        self.ref_cliente_input = QLineEdit()
        self.enc_phc_input = QLineEdit()
        self.info_1_input = QTextEdit()
        self.info_1_input.setFixedHeight(60)
        self.info_2_input = QTextEdit()
        self.info_2_input.setFixedHeight(60)

        self.utilizador_combo = QComboBox()
        self._carregar_utilizadores()

        self.margens_combo = QComboBox()
        self.margens_combo.setToolTip(self.MARGENS_TOOLTIP)
        self.margens_combo.addItem("Standard", AMBITO_STANDARD)
        self.margens_combo.addItem("Do cliente", AMBITO_CLIENTE)
        self.margens_combo.addItem("Do utilizador", AMBITO_UTILIZADOR)
        self._carregar_disponibilidade_margens()
        # The customer option follows the typed name/email.
        self.nome_cliente_input.editingFinished.connect(
            self._atualizar_opcao_margens_cliente
        )
        self.email_cliente_input.editingFinished.connect(
            self._atualizar_opcao_margens_cliente
        )

        self.error_label = QLabel("")
        self.error_label.setObjectName("novoOrcamentoError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Nome cliente", self.nome_cliente_input)
        form_layout.addRow("Email cliente", self.email_cliente_input)
        form_layout.addRow("Telefone cliente", self.telefone_cliente_input)
        form_layout.addRow("Obra", self.obra_input)
        form_layout.addRow("Descrição", self.descricao_input)
        form_layout.addRow("Localização", self.localizacao_input)
        form_layout.addRow("Ref. cliente", self.ref_cliente_input)
        form_layout.addRow("Enc. PHC", self.enc_phc_input)
        form_layout.addRow("Info 1", self.info_1_input)
        form_layout.addRow("Info 2", self.info_2_input)
        form_layout.addRow("Utilizador", self.utilizador_combo)
        form_layout.addRow("Margens iniciais:", self.margens_combo)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def get_data(self) -> NovoOrcamentoDialogData:
        """Return normalized dialog data."""
        return NovoOrcamentoDialogData(
            nome_cliente=self.nome_cliente_input.text().strip(),
            email_cliente=self._empty_to_none(self.email_cliente_input.text()),
            telefone_cliente=self._empty_to_none(self.telefone_cliente_input.text()),
            obra=self.obra_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            localizacao=self._empty_to_none(self.localizacao_input.text()),
            ref_cliente=self._empty_to_none(self.ref_cliente_input.text()),
            enc_phc=self._empty_to_none(self.enc_phc_input.text()),
            info_1=self._empty_to_none(self.info_1_input.toPlainText()),
            info_2=self._empty_to_none(self.info_2_input.toPlainText()),
            margens_escolha=self.margens_combo.currentData() or AMBITO_STANDARD,
            utilizador_id=self.utilizador_combo.currentData(),
        )

    def _carregar_utilizadores(self) -> None:
        """Populate the active-users combo, preselecting the logged-in user."""
        try:
            with SessionLocal() as session:
                utilizadores = UserRepository(session).list_active_users()
        except SQLAlchemyError:
            utilizadores = []

        self.utilizador_combo.clear()
        for utilizador in utilizadores:
            self.utilizador_combo.addItem(utilizador.username, utilizador.id)

        current_user = app_session.current_user
        if current_user is None:
            return

        index = self.utilizador_combo.findData(current_user.id)
        if index >= 0:
            self.utilizador_combo.setCurrentIndex(index)

    def _carregar_disponibilidade_margens(self) -> None:
        """Enable the margin options that have an applicable record."""
        current_user = app_session.current_user
        tem_margens_user = False
        if current_user is not None:
            try:
                with SessionLocal() as session:
                    tem_margens_user = (
                        DefMargemPadraoService(session).margens_utilizador(
                            current_user.id
                        )
                        is not None
                    )
            except SQLAlchemyError:
                tem_margens_user = False

        self._set_opcao_margens_enabled(AMBITO_UTILIZADOR, tem_margens_user)
        self._atualizar_opcao_margens_cliente()

    def _atualizar_opcao_margens_cliente(self) -> None:
        """Enable 'Do cliente' when the typed customer has its own margins."""
        try:
            with SessionLocal() as session:
                margens = DefMargemPadraoService(session).margens_cliente_por_contacto(
                    self.nome_cliente_input.text(),
                    self.email_cliente_input.text(),
                )
        except SQLAlchemyError:
            margens = None

        self._set_opcao_margens_enabled(AMBITO_CLIENTE, margens is not None)

    def _set_opcao_margens_enabled(self, ambito: str, enabled: bool) -> None:
        """Enable/disable one margins-combo option, resetting if selected."""
        index = self.margens_combo.findData(ambito)
        if index < 0:
            return

        item = self.margens_combo.model().item(index)
        if item is None:
            return

        flags = item.flags()
        if enabled:
            item.setFlags(flags | Qt.ItemFlag.ItemIsEnabled)
        else:
            item.setFlags(flags & ~Qt.ItemFlag.ItemIsEnabled)
            if self.margens_combo.currentIndex() == index:
                self.margens_combo.setCurrentIndex(
                    self.margens_combo.findData(AMBITO_STANDARD)
                )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        data = self.get_data()

        if not data.nome_cliente:
            self.error_label.setText("O nome do cliente e obrigatorio.")
            return

        self.accept()

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None
