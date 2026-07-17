"""Dialog for creating a simple Orcamento."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.margens_padrao_types import (
    AMBITO_CLIENTE,
    AMBITO_CLIENTE_FINAL,
    AMBITO_STANDARD,
    AMBITO_UTILIZADOR,
)
from app.repositories.user_repository import UserRepository
from app.services.def_margem_padrao_service import DefMargemPadraoService
from app.services.system_setting_service import SystemSettingService


@dataclass(frozen=True, kw_only=True)
class NovoOrcamentoDialogData:
    """Data collected by the new budget dialog."""

    cliente_id: int | None = None
    obra: str
    descricao: str | None
    localizacao: str | None
    ref_cliente: str | None
    enc_phc: str | None = None
    info_1: str | None = None
    info_2: str | None = None
    margens_escolha: str = AMBITO_STANDARD
    utilizador_id: int | None = None
    # Registo manual (orçamento antigo): ano + número indicados pelo
    # utilizador e pasta de servidor já existente.
    manual: bool = False
    ano: int | None = None
    num_orcamento: str | None = None
    pasta_manual: str | None = None


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

        self._cliente_id: int | None = None
        self.cliente_label = QLabel("\u2014 nenhum cliente escolhido \u2014")
        self.escolher_cliente_button = QPushButton("Escolher cliente\u2026")
        self.escolher_cliente_button.clicked.connect(self._escolher_cliente)
        cliente_widget = QWidget()
        cliente_layout = QHBoxLayout(cliente_widget)
        cliente_layout.setContentsMargins(0, 0, 0, 0)
        cliente_layout.addWidget(self.cliente_label, stretch=1)
        cliente_layout.addWidget(self.escolher_cliente_button)

        self.antigo_checkbox = QCheckBox("Orçamento antigo (registo manual)")
        self.antigo_checkbox.setToolTip(
            "Registar um orçamento antigo (pré-V3): o ano e o número são "
            "indicados manualmente e os ficheiros (PDF, Excel, relatórios) "
            "gravam diretamente na pasta de servidor escolhida abaixo."
        )
        self.antigo_checkbox.toggled.connect(self._toggle_modo_antigo)

        self.ano_input = QSpinBox()
        self.ano_input.setRange(2000, date.today().year)
        self.ano_input.setValue(date.today().year - 1)
        self.ano_input.setToolTip("Ano do orçamento antigo (ex.: 2025).")

        self.num_orcamento_input = QLineEdit()
        self.num_orcamento_input.setToolTip(
            "Número do orçamento antigo, tal como usado na pasta do servidor "
            "(ex.: 1049)."
        )

        self._pasta_manual: str | None = None
        self.pasta_label = QLabel("— nenhuma pasta escolhida —")
        self.pasta_label.setWordWrap(True)
        self.pasta_label.setToolTip(
            "Pasta do servidor onde os ficheiros deste orçamento serão "
            "gravados (PDF, Excel, relatórios)."
        )
        self.escolher_pasta_button = QPushButton("Escolher pasta…")
        self.escolher_pasta_button.setToolTip(
            "Selecionar a pasta já existente do orçamento antigo no servidor."
        )
        self.escolher_pasta_button.clicked.connect(self._escolher_pasta)
        pasta_widget = QWidget()
        pasta_layout = QHBoxLayout(pasta_widget)
        pasta_layout.setContentsMargins(0, 0, 0, 0)
        pasta_layout.addWidget(self.pasta_label, stretch=1)
        pasta_layout.addWidget(self.escolher_pasta_button)
        self._pasta_widget = pasta_widget

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
        self.margens_combo.addItem("Cliente Final", AMBITO_CLIENTE_FINAL)
        self._carregar_disponibilidade_margens()

        self.error_label = QLabel("")
        self.error_label.setObjectName("novoOrcamentoError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Cliente", cliente_widget)
        form_layout.addRow("", self.antigo_checkbox)
        form_layout.addRow("Ano", self.ano_input)
        form_layout.addRow("N.º orçamento", self.num_orcamento_input)
        form_layout.addRow("Pasta do orçamento", pasta_widget)
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

        self._form_layout = form_layout
        self._toggle_modo_antigo(False)

    def get_data(self) -> NovoOrcamentoDialogData:
        """Return normalized dialog data."""
        manual = self.antigo_checkbox.isChecked()
        return NovoOrcamentoDialogData(
            cliente_id=self._cliente_id,
            obra=self.obra_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            localizacao=self._empty_to_none(self.localizacao_input.text()),
            ref_cliente=self._empty_to_none(self.ref_cliente_input.text()),
            enc_phc=self._empty_to_none(self.enc_phc_input.text()),
            info_1=self._empty_to_none(self.info_1_input.toPlainText()),
            info_2=self._empty_to_none(self.info_2_input.toPlainText()),
            margens_escolha=self.margens_combo.currentData() or AMBITO_STANDARD,
            utilizador_id=self.utilizador_combo.currentData(),
            manual=manual,
            ano=self.ano_input.value() if manual else None,
            num_orcamento=(
                self._empty_to_none(self.num_orcamento_input.text())
                if manual
                else None
            ),
            pasta_manual=self._pasta_manual if manual else None,
        )

    def _toggle_modo_antigo(self, checked: bool) -> None:
        """Show/hide the manual fields of the legacy-budget mode."""
        self._form_layout.setRowVisible(self.ano_input, checked)
        self._form_layout.setRowVisible(self.num_orcamento_input, checked)
        self._form_layout.setRowVisible(self._pasta_widget, checked)
        self.error_label.setText("")
        self.adjustSize()

    def _escolher_pasta(self) -> None:
        """Pick the existing server folder of the legacy budget."""
        inicio = ""
        try:
            with SessionLocal() as session:
                base = SystemSettingService(session).obter_valor(
                    "pasta_base_orcamentos"
                )
        except SQLAlchemyError:
            base = None

        if base:
            candidato = Path(base) / str(self.ano_input.value())
            if candidato.exists():
                inicio = str(candidato)
            elif Path(base).exists():
                inicio = base

        pasta = QFileDialog.getExistingDirectory(
            self,
            "Escolher pasta do orçamento",
            inicio,
        )
        if not pasta:
            return

        self._pasta_manual = pasta
        self.pasta_label.setText(pasta)

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

    def _escolher_cliente(self) -> None:
        from app.ui.dialogs.selecionar_cliente_dialog import SelecionarClienteDialog

        dialog = SelecionarClienteDialog(self)
        if not dialog.exec() or dialog.selected_cliente is None:
            return

        cliente = dialog.selected_cliente
        self._cliente_id = cliente.id
        tipo = "Tempor\u00e1rio" if cliente.is_temporary else "PHC"
        self.cliente_label.setText(f"{cliente.nome} ({tipo})")
        self._atualizar_opcao_margens_cliente()

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
        try:
            with SessionLocal() as session:
                tem_cliente_final = (
                    DefMargemPadraoService(session).obter_cliente_final() is not None
                )
        except SQLAlchemyError:
            tem_cliente_final = False
        self._set_opcao_margens_enabled(AMBITO_CLIENTE_FINAL, tem_cliente_final)
        self._atualizar_opcao_margens_cliente()

    def _atualizar_opcao_margens_cliente(self) -> None:
        """Enable 'Do cliente' when the selected customer has its own margins."""
        try:
            with SessionLocal() as session:
                margens = DefMargemPadraoService(session).margens_cliente(
                    self._cliente_id
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

        if data.cliente_id is None:
            self.error_label.setText("Escolha um cliente.")
            return

        if data.manual:
            if not data.num_orcamento:
                self.error_label.setText(
                    "Indique o número do orçamento antigo."
                )
                return
            if not data.pasta_manual:
                self.error_label.setText(
                    "Escolha a pasta do orçamento no servidor."
                )
                return
            if not Path(data.pasta_manual).exists():
                self.error_label.setText(
                    f"A pasta escolhida não existe:\n{data.pasta_manual}"
                )
                return

        self.accept()

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None
