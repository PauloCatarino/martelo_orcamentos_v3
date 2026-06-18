"""Dialog for editing an Orcamento's general data (phase 9.0)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.orcamento_estados import ESTADOS_ORCAMENTO
from app.repositories.cliente_repository import ClienteListaResumo
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class EditarOrcamentoDialogData:
    """Data shown/collected by the edit budget dialog."""

    obra: str
    descricao: str | None
    localizacao: str | None
    ref_cliente: str | None
    estado: str
    enc_phc: str | None = None
    info_1: str | None = None
    info_2: str | None = None
    utilizador_id: int | None = None
    cliente_id: int | None = None


@dataclass(frozen=True)
class EditarOrcamentoContexto:
    """Display context for the edit budget dialog."""

    num_orcamento: str
    numero_versao: int
    codigo_versao: str
    cliente: ClienteListaResumo | None = None


class EditarOrcamentoDialog(QDialog):
    """Simple modal dialog to edit a budget's general data."""

    def __init__(
        self,
        parent=None,
        dados: EditarOrcamentoDialogData | None = None,
        *,
        contexto: EditarOrcamentoContexto | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Editar Orçamento")
        self.setModal(True)
        self.setMinimumWidth(460)

        self._cliente_id: int | None = None

        self.header_label = QLabel("")
        self.header_label.setObjectName("editarOrcamentoHeader")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.cliente_nome_label = QLabel("\u2014")
        self.cliente_simplex_label = QLabel("\u2014")
        self.cliente_email_label = QLabel("\u2014")
        self.cliente_telefone_label = QLabel("\u2014")
        self.cliente_tipo_label = QLabel("\u2014")
        self.trocar_cliente_button = QPushButton("Trocar cliente\u2026")
        self.trocar_cliente_button.clicked.connect(self._trocar_cliente)

        cliente_form = QFormLayout()
        cliente_form.addRow("Nome", self.cliente_nome_label)
        cliente_form.addRow("Simplex", self.cliente_simplex_label)
        cliente_form.addRow("Email", self.cliente_email_label)
        cliente_form.addRow("Telefone", self.cliente_telefone_label)
        cliente_form.addRow("Tipo", self.cliente_tipo_label)
        cliente_form.addRow("", self.trocar_cliente_button)
        self.cliente_group = QGroupBox("Cliente")
        self.cliente_group.setLayout(cliente_form)

        self.estado_combo = QComboBox()
        self.estado_combo.setEditable(False)
        self.estado_combo.addItems(list(ESTADOS_ORCAMENTO))
        self.utilizador_combo = QComboBox()
        self._carregar_utilizadores()
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

        # Pre-fill from the received data.
        if dados is not None:
            estado_atual = dados.estado or ""
            if estado_atual and self.estado_combo.findText(estado_atual) < 0:
                self.estado_combo.addItem(estado_atual)
            if estado_atual:
                self.estado_combo.setCurrentText(estado_atual)
            if dados.utilizador_id is not None:
                index = self.utilizador_combo.findData(dados.utilizador_id)
                if index >= 0:
                    self.utilizador_combo.setCurrentIndex(index)
            self.obra_input.setText(dados.obra or "")
            self.descricao_input.setPlainText(dados.descricao or "")
            self.localizacao_input.setText(dados.localizacao or "")
            self.ref_cliente_input.setText(dados.ref_cliente or "")
            self.enc_phc_input.setText(dados.enc_phc or "")
            self.info_1_input.setPlainText(dados.info_1 or "")
            self.info_2_input.setPlainText(dados.info_2 or "")

        if contexto is not None:
            self.header_label.setText(
                f"Or\u00e7amento {contexto.codigo_versao}  \u00b7  "
                f"N\u00ba {contexto.num_orcamento}  \u00b7  "
                f"Vers\u00e3o {contexto.numero_versao:02d}"
            )
            self._cliente_id = contexto.cliente.id if contexto.cliente else None
            self._atualizar_painel_cliente(contexto.cliente)
        elif dados is not None:
            self._cliente_id = dados.cliente_id

        self.error_label = QLabel("")
        self.error_label.setObjectName("editarOrcamentoError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Estado", self.estado_combo)
        form_layout.addRow("Utilizador", self.utilizador_combo)
        form_layout.addRow("Obra", self.obra_input)
        form_layout.addRow("Descrição", self.descricao_input)
        form_layout.addRow("Localização", self.localizacao_input)
        form_layout.addRow("Ref. cliente", self.ref_cliente_input)
        form_layout.addRow("Enc. PHC", self.enc_phc_input)
        form_layout.addRow("Info 1", self.info_1_input)
        form_layout.addRow("Info 2", self.info_2_input)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.header_label)
        layout.addWidget(self.cliente_group)
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def get_data(self) -> EditarOrcamentoDialogData:
        """Return normalized dialog data."""
        return EditarOrcamentoDialogData(
            obra=self.obra_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            localizacao=self._empty_to_none(self.localizacao_input.text()),
            ref_cliente=self._empty_to_none(self.ref_cliente_input.text()),
            estado=self.estado_combo.currentText(),
            enc_phc=self._empty_to_none(self.enc_phc_input.text()),
            info_1=self._empty_to_none(self.info_1_input.toPlainText()),
            info_2=self._empty_to_none(self.info_2_input.toPlainText()),
            utilizador_id=self.utilizador_combo.currentData(),
            cliente_id=self._cliente_id,
        )

    def _carregar_utilizadores(self) -> None:
        """Populate the active-users combo."""
        try:
            with SessionLocal() as session:
                utilizadores = UserRepository(session).list_active_users()
        except SQLAlchemyError:
            utilizadores = []

        self.utilizador_combo.clear()
        for utilizador in utilizadores:
            self.utilizador_combo.addItem(utilizador.username, utilizador.id)

    def _atualizar_painel_cliente(self, cliente: ClienteListaResumo | None) -> None:
        if cliente is None:
            for label in (
                self.cliente_nome_label,
                self.cliente_simplex_label,
                self.cliente_email_label,
                self.cliente_telefone_label,
                self.cliente_tipo_label,
            ):
                label.setText("\u2014")
            return

        self.cliente_nome_label.setText(cliente.nome or "\u2014")
        self.cliente_simplex_label.setText(cliente.nome_simplex or "\u2014")
        self.cliente_email_label.setText(cliente.email or "\u2014")
        self.cliente_telefone_label.setText(
            cliente.telefone or cliente.telemovel or "\u2014"
        )
        self.cliente_tipo_label.setText(
            "Tempor\u00e1rio" if cliente.is_temporary else "PHC"
        )

    def _trocar_cliente(self) -> None:
        from app.ui.dialogs.selecionar_cliente_dialog import SelecionarClienteDialog

        dialog = SelecionarClienteDialog(self)
        if not dialog.exec() or dialog.selected_cliente is None:
            return

        cliente = dialog.selected_cliente
        self._cliente_id = cliente.id
        self._atualizar_painel_cliente(cliente)

    def _validate_and_accept(self) -> None:
        """Accept edits; all fields in this dialog are optional."""
        self.accept()

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None
