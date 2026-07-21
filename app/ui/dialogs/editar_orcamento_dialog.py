"""Dialog for editing an Orcamento's general data (phase 9.0)."""

from __future__ import annotations
from app.ui import tema

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.orcamento_estados import ESTADOS_ORCAMENTO
from app.repositories.cliente_repository import ClienteListaResumo
from app.repositories.user_repository import UserRepository
from app.services.orcamento_encomenda_phc_service import EncomendaPhcInput


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
    # Phase 5: every PHC order of the version (the principal one is mirrored
    # into enc_phc). An empty tuple means the version has no orders.
    encomendas_phc: tuple[EncomendaPhcInput, ...] = ()


@dataclass(frozen=True)
class EditarOrcamentoContexto:
    """Display context for the edit budget dialog."""

    num_orcamento: str
    numero_versao: int
    codigo_versao: str
    cliente: ClienteListaResumo | None = None
    # Next version number for this budget: enables the "Duplicar para versão…"
    # action (which saves the whole content into a brand new version).
    proxima_versao: int | None = None


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
        self._proxima_versao: int | None = None
        # Set when the user chose "Duplicar para versão…" instead of "Guardar".
        self.duplicar_versao_requested = False

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

        # Phase 5: management of the version's PHC orders. The list keeps
        # (numero, is_principal) pairs; the principal shows a star prefix.
        self.encomendas_list = QListWidget()
        self.encomendas_list.setMaximumHeight(88)
        self.encomendas_list.setToolTip(
            "Encomendas PHC desta versão; a principal (★) aparece nas listas"
        )
        self.nova_encomenda_input = QLineEdit()
        self.nova_encomenda_input.setPlaceholderText("Número da encomenda PHC")
        self.nova_encomenda_input.setToolTip(
            "Escreva o número da encomenda PHC e clique Adicionar"
        )
        self.adicionar_encomenda_button = QPushButton("Adicionar")
        self.adicionar_encomenda_button.setToolTip(
            "Adicionar a encomenda PHC à versão"
        )
        self.adicionar_encomenda_button.clicked.connect(self._adicionar_encomenda)
        self.nova_encomenda_input.returnPressed.connect(self._adicionar_encomenda)
        self.remover_encomenda_button = QPushButton("Remover")
        self.remover_encomenda_button.setToolTip(
            "Remover a encomenda PHC selecionada"
        )
        self.remover_encomenda_button.clicked.connect(self._remover_encomenda)
        self.principal_encomenda_button = QPushButton("Principal")
        self.principal_encomenda_button.setToolTip(
            "Marcar a encomenda selecionada como principal"
        )
        self.principal_encomenda_button.clicked.connect(self._definir_principal)

        adicionar_layout = QHBoxLayout()
        adicionar_layout.addWidget(self.nova_encomenda_input, stretch=1)
        adicionar_layout.addWidget(self.adicionar_encomenda_button)
        acoes_layout = QHBoxLayout()
        acoes_layout.addWidget(self.remover_encomenda_button)
        acoes_layout.addWidget(self.principal_encomenda_button)
        acoes_layout.addStretch()
        encomendas_layout = QVBoxLayout()
        encomendas_layout.addLayout(adicionar_layout)
        encomendas_layout.addWidget(self.encomendas_list)
        encomendas_layout.addLayout(acoes_layout)
        self.encomendas_group = QGroupBox("Encomendas PHC")
        self.encomendas_group.setLayout(encomendas_layout)

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
            encomendas = list(dados.encomendas_phc)
            if not encomendas and (dados.enc_phc or "").strip():
                # Legacy version: the old single number is the principal one.
                encomendas = [
                    EncomendaPhcInput(
                        numero=dados.enc_phc.strip(), is_principal=True
                    )
                ]
            for encomenda in encomendas:
                self._inserir_encomenda(encomenda.numero, encomenda.is_principal)
            self.info_1_input.setPlainText(dados.info_1 or "")
            self.info_2_input.setPlainText(dados.info_2 or "")

        if contexto is not None:
            self.header_label.setText(
                f"Or\u00e7amento {contexto.codigo_versao}  \u00b7  "
                f"N\u00ba {contexto.num_orcamento}  \u00b7  "
                f"Vers\u00e3o {contexto.numero_versao:02d}"
            )
            self._cliente_id = contexto.cliente.id if contexto.cliente else None
            self._proxima_versao = contexto.proxima_versao
            self._atualizar_painel_cliente(contexto.cliente)
        elif dados is not None:
            self._cliente_id = dados.cliente_id

        self.error_label = QLabel("")
        self.error_label.setObjectName("editarOrcamentoError")
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Estado", self.estado_combo)
        form_layout.addRow("Utilizador", self.utilizador_combo)
        form_layout.addRow("Obra", self.obra_input)
        form_layout.addRow("Descrição", self.descricao_input)
        form_layout.addRow("Localização", self.localizacao_input)
        form_layout.addRow("Ref. cliente", self.ref_cliente_input)
        form_layout.addRow(self.encomendas_group)
        form_layout.addRow("Info 1", self.info_1_input)
        form_layout.addRow("Info 2", self.info_2_input)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        # "Duplicar para versão NN…": save the whole budget as a brand-new
        # version of the same budget (the source stays untouched).
        rotulo_duplicar = (
            f"Duplicar para versão {self._proxima_versao:02d}…"
            if self._proxima_versao is not None
            else "Duplicar para nova versão…"
        )
        self.duplicar_versao_button = self.button_box.addButton(
            rotulo_duplicar, QDialogButtonBox.ButtonRole.ActionRole
        )
        self.duplicar_versao_button.setToolTip(
            "Cria uma nova versão deste orçamento com todo o conteúdo "
            "(itens, custeio e ValueSet), sem alterar a versão atual."
        )
        self.duplicar_versao_button.setVisible(self._proxima_versao is not None)
        self.duplicar_versao_button.clicked.connect(self._duplicar_versao)
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
        encomendas = self._encomendas_atuais()
        principal = next(
            (enc.numero for enc in encomendas if enc.is_principal), None
        )
        return EditarOrcamentoDialogData(
            obra=self.obra_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            localizacao=self._empty_to_none(self.localizacao_input.text()),
            ref_cliente=self._empty_to_none(self.ref_cliente_input.text()),
            estado=self.estado_combo.currentText(),
            enc_phc=principal,
            info_1=self._empty_to_none(self.info_1_input.toPlainText()),
            info_2=self._empty_to_none(self.info_2_input.toPlainText()),
            utilizador_id=self.utilizador_combo.currentData(),
            cliente_id=self._cliente_id,
            encomendas_phc=tuple(encomendas),
        )

    def _encomendas_atuais(self) -> list[EncomendaPhcInput]:
        """Return the PHC orders currently shown in the list."""
        encomendas: list[EncomendaPhcInput] = []
        for index in range(self.encomendas_list.count()):
            item = self.encomendas_list.item(index)
            numero, is_principal = item.data(Qt.ItemDataRole.UserRole)
            encomendas.append(
                EncomendaPhcInput(numero=numero, is_principal=is_principal)
            )
        return encomendas

    def _inserir_encomenda(self, numero: str, is_principal: bool) -> None:
        """Append one PHC order row to the list widget."""
        prefixo = "★ " if is_principal else "    "
        item = QListWidgetItem(f"{prefixo}{numero}")
        item.setData(Qt.ItemDataRole.UserRole, (numero, is_principal))
        item.setToolTip(
            "Encomenda principal" if is_principal else "Encomenda adicional"
        )
        self.encomendas_list.addItem(item)

    def _redesenhar_encomendas(
        self, encomendas: list[EncomendaPhcInput], selecionar: str | None = None
    ) -> None:
        """Rebuild the list keeping exactly one principal order."""
        if encomendas and not any(enc.is_principal for enc in encomendas):
            encomendas[0] = EncomendaPhcInput(
                numero=encomendas[0].numero, is_principal=True
            )
        self.encomendas_list.clear()
        for encomenda in encomendas:
            self._inserir_encomenda(encomenda.numero, encomenda.is_principal)
        if selecionar is not None:
            for index in range(self.encomendas_list.count()):
                item = self.encomendas_list.item(index)
                if item.data(Qt.ItemDataRole.UserRole)[0] == selecionar:
                    self.encomendas_list.setCurrentItem(item)
                    break

    def _adicionar_encomenda(self) -> None:
        numero = self.nova_encomenda_input.text().strip()
        if not numero:
            return
        encomendas = self._encomendas_atuais()
        if numero.casefold() in {enc.numero.casefold() for enc in encomendas}:
            self.error_label.setText(
                f"A encomenda PHC '{numero}' já existe nesta versão."
            )
            return
        self.error_label.setText("")
        encomendas.append(
            EncomendaPhcInput(numero=numero, is_principal=not encomendas)
        )
        self._redesenhar_encomendas(encomendas, selecionar=numero)
        self.nova_encomenda_input.clear()

    def _remover_encomenda(self) -> None:
        item = self.encomendas_list.currentItem()
        if item is None:
            return
        numero, _is_principal = item.data(Qt.ItemDataRole.UserRole)
        encomendas = [
            enc for enc in self._encomendas_atuais() if enc.numero != numero
        ]
        self.error_label.setText("")
        self._redesenhar_encomendas(encomendas)

    def _definir_principal(self) -> None:
        item = self.encomendas_list.currentItem()
        if item is None:
            return
        numero, _is_principal = item.data(Qt.ItemDataRole.UserRole)
        encomendas = [
            EncomendaPhcInput(
                numero=enc.numero, is_principal=enc.numero == numero
            )
            for enc in self._encomendas_atuais()
        ]
        self.error_label.setText("")
        self._redesenhar_encomendas(encomendas, selecionar=numero)

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
        self.duplicar_versao_requested = False
        self.accept()

    def _duplicar_versao(self) -> None:
        """Accept the dialog signalling a duplicate-to-new-version request."""
        self.duplicar_versao_requested = True
        self.accept()

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None
