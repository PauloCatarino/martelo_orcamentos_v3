"""Dialog for creating and editing a machine."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.repositories.def_maquina_repository import DefMaquinaResumo

TIPO_OPCOES = ("CORTE", "ORLAGEM", "CNC", "MONTAGEM", "MANUAL", "OUTRO")

# Spin-box sentinel for "not set" (kept as None when saving).
_SEM_VALOR = -1.0


@dataclass(frozen=True)
class MaquinaDialogData:
    """Data collected by the machine dialog."""

    codigo: str
    nome: str
    descricao: str | None
    tipo: str | None
    custo_hora: Decimal | None
    custo_hora_serie: Decimal | None
    preco_ml_std: Decimal | None
    preco_ml_serie: Decimal | None
    preco_lado_curto_std: Decimal | None
    preco_lado_curto_serie: Decimal | None
    preco_lado_longo_std: Decimal | None
    preco_lado_longo_serie: Decimal | None
    limite_lado_mm: Decimal | None
    custo_setup_peca_std: Decimal | None
    custo_setup_peca_serie: Decimal | None
    observacoes: str | None
    ativo: bool


class MaquinaDialog(QDialog):
    """Modal dialog for creating or editing a machine.

    The tariff fields show their unit as a suffix and adapt to the machine type:
    corte uses €/ML + setup/piece; orlagem uses €/side by side measure +
    setup/piece; CNC keeps €/hour (informative) plus the area-tier editor;
    manual/montagem use €/hour only.
    """

    def __init__(
        self,
        maquina: DefMaquinaResumo | None = None,
        parent=None,
        on_save: Callable[[MaquinaDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.maquina = maquina
        self.on_save = on_save
        self._is_edit = maquina is not None

        self.setWindowTitle("Editar Máquina" if self._is_edit else "Nova Máquina")
        self.setModal(True)
        self.setMinimumWidth(480)

        self.codigo_input = QLineEdit()
        self.nome_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(70)
        self.tipo_input = QComboBox()
        for opcao in TIPO_OPCOES:
            self.tipo_input.addItem(opcao, opcao)
        self.observacoes_input = QLineEdit()
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        # Tariff inputs (unit shown as suffix; Decimal kept on save).
        self.custo_hora_input = self._criar_spin(" €/H")
        self.custo_hora_serie_input = self._criar_spin(" €/H")
        self.preco_ml_std_input = self._criar_spin(" €/ML")
        self.preco_ml_serie_input = self._criar_spin(" €/ML")
        self.preco_lado_curto_std_input = self._criar_spin(" €/lado")
        self.preco_lado_curto_serie_input = self._criar_spin(" €/lado")
        self.preco_lado_longo_std_input = self._criar_spin(" €/lado")
        self.preco_lado_longo_serie_input = self._criar_spin(" €/lado")
        self.limite_lado_mm_input = self._criar_spin(" mm")
        self.custo_setup_peca_std_input = self._criar_spin(" €/peça")
        self.custo_setup_peca_serie_input = self._criar_spin(" €/peça")

        self.error_label = QLabel("")
        self.error_label.setObjectName("maquinaDialogError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        self.info_label = QLabel(
            "Tarifas por máquina (STD = peça única, SERIE = lote): corte é "
            "cobrado ao €/ML; orlagem ao € por lado orlado, com 2 escalões pela "
            "medida do lado; o CNC por escalões de área; manual e montagem ao "
            "€/hora."
        )
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #666666; font-size: 11px;")

        form_basico = QFormLayout()
        form_basico.addRow("Código", self.codigo_input)
        form_basico.addRow("Nome", self.nome_input)
        form_basico.addRow("Descrição", self.descricao_input)
        form_basico.addRow("Tipo", self.tipo_input)

        self.hora_section = self._criar_section(
            [
                ("Custo/hora STD", self.custo_hora_input),
                ("Custo/hora SERIE", self.custo_hora_serie_input),
            ]
        )
        self.ml_section = self._criar_section(
            [
                ("€/ML STD", self.preco_ml_std_input),
                ("€/ML SERIE", self.preco_ml_serie_input),
            ]
        )
        self.orlagem_section = self._criar_section(
            [
                ("€/lado ≤ limite STD", self.preco_lado_curto_std_input),
                ("€/lado ≤ limite SERIE", self.preco_lado_curto_serie_input),
                ("€/lado > limite STD", self.preco_lado_longo_std_input),
                ("€/lado > limite SERIE", self.preco_lado_longo_serie_input),
                ("Limite do lado (mm)", self.limite_lado_mm_input),
            ]
        )
        self.setup_section = self._criar_section(
            [
                ("Setup €/peça STD", self.custo_setup_peca_std_input),
                ("Setup €/peça SERIE", self.custo_setup_peca_serie_input),
            ]
        )
        self.cnc_section = self._criar_cnc_section()

        form_final = QFormLayout()
        form_final.addRow("Observações", self.observacoes_input)
        form_final.addRow("Ativo", self.ativo_input)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.info_label)
        layout.addLayout(form_basico)
        layout.addWidget(self.hora_section)
        layout.addWidget(self.ml_section)
        layout.addWidget(self.orlagem_section)
        layout.addWidget(self.setup_section)
        layout.addWidget(self.cnc_section)
        layout.addLayout(form_final)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.tipo_input.currentIndexChanged.connect(self._update_tarifas_visiveis)

        if maquina is not None:
            self._load_maquina(maquina)
        self._update_tarifas_visiveis()

    def _criar_spin(self, suffix: str) -> QDoubleSpinBox:
        """Build a tariff spin box that shows ``suffix`` and an empty special value."""
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setRange(_SEM_VALOR, 9_999_999.0)
        spin.setSpecialValueText("")  # blank when "not set" (value == minimum)
        spin.setSuffix(suffix)
        spin.setValue(_SEM_VALOR)
        return spin

    def _criar_section(self, linhas: list[tuple[str, QWidget]]) -> QWidget:
        """Build a form-based section widget that can be shown/hidden as a whole."""
        section = QWidget()
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        for label, widget in linhas:
            form.addRow(label, widget)
        section.setLayout(form)
        return section

    def _criar_cnc_section(self) -> QWidget:
        """Build the CNC note + area-tier button section."""
        section = QWidget()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)

        self.cnc_note = QLabel("O preço por peça do CNC é definido nos escalões de área.")
        self.cnc_note.setWordWrap(True)
        self.cnc_note.setStyleSheet("color: #666666; font-size: 11px;")

        self.escaloes_button = QPushButton("Escalões de área...")
        if self._is_edit and self.maquina is not None:
            self.escaloes_button.clicked.connect(self._abrir_escaloes)
        else:
            self.escaloes_button.setEnabled(False)
            self.cnc_note.setText(
                "O preço por peça do CNC é definido nos escalões de área. "
                "Grave a máquina primeiro para os poder definir."
            )

        vbox.addWidget(self.cnc_note)
        row = QHBoxLayout()
        row.addWidget(self.escaloes_button)
        row.addStretch()
        vbox.addLayout(row)
        section.setLayout(vbox)
        return section

    def _abrir_escaloes(self) -> None:
        """Open the CNC area-tier editor for this (already saved) machine."""
        from app.ui.dialogs.escaloes_area_dialog import EscaloesAreaDialog

        rotulo = f"Máquina: {self.maquina.codigo} - {self.maquina.nome}"
        EscaloesAreaDialog(self.maquina.id, maquina_label=rotulo, parent=self).exec()

    def _update_tarifas_visiveis(self) -> None:
        """Show only the tariff fields that apply to the selected machine type."""
        tipo = (self.tipo_input.currentData() or "").upper()
        if tipo == "CORTE":
            mostrar_hora, mostrar_ml, mostrar_orlagem, mostrar_setup, mostrar_cnc = (
                False,
                True,
                False,
                True,
                False,
            )
        elif tipo == "ORLAGEM":
            mostrar_hora, mostrar_ml, mostrar_orlagem, mostrar_setup, mostrar_cnc = (
                False,
                False,
                True,
                True,
                False,
            )
        elif tipo == "CNC":
            mostrar_hora, mostrar_ml, mostrar_orlagem, mostrar_setup, mostrar_cnc = (
                True,
                False,
                False,
                False,
                True,
            )
        elif tipo in ("MANUAL", "MONTAGEM"):
            mostrar_hora, mostrar_ml, mostrar_orlagem, mostrar_setup, mostrar_cnc = (
                True,
                False,
                False,
                False,
                False,
            )
        else:  # empty or other -> show all tariff fields (current behaviour)
            mostrar_hora, mostrar_ml, mostrar_orlagem, mostrar_setup, mostrar_cnc = (
                True,
                True,
                True,
                True,
                False,
            )

        self.hora_section.setVisible(mostrar_hora)
        self.ml_section.setVisible(mostrar_ml)
        self.orlagem_section.setVisible(mostrar_orlagem)
        self.setup_section.setVisible(mostrar_setup)
        self.cnc_section.setVisible(mostrar_cnc)

    def _load_maquina(self, maquina: DefMaquinaResumo) -> None:
        """Populate the form with an existing machine and lock the code."""
        self.codigo_input.setText(maquina.codigo)
        self.codigo_input.setReadOnly(True)
        self.nome_input.setText(maquina.nome)
        self.descricao_input.setPlainText(maquina.descricao or "")
        self._select_tipo(maquina.tipo)
        self._set_spin(self.custo_hora_input, maquina.custo_hora)
        self._set_spin(self.custo_hora_serie_input, maquina.custo_hora_serie)
        self._set_spin(self.preco_ml_std_input, maquina.preco_ml_std)
        self._set_spin(self.preco_ml_serie_input, maquina.preco_ml_serie)
        self._set_spin(self.preco_lado_curto_std_input, maquina.preco_lado_curto_std)
        self._set_spin(
            self.preco_lado_curto_serie_input, maquina.preco_lado_curto_serie
        )
        self._set_spin(self.preco_lado_longo_std_input, maquina.preco_lado_longo_std)
        self._set_spin(
            self.preco_lado_longo_serie_input, maquina.preco_lado_longo_serie
        )
        self._set_spin(self.limite_lado_mm_input, maquina.limite_lado_mm)
        self._set_spin(self.custo_setup_peca_std_input, maquina.custo_setup_peca_std)
        self._set_spin(self.custo_setup_peca_serie_input, maquina.custo_setup_peca_serie)
        self.observacoes_input.setText(maquina.observacoes or "")
        self.ativo_input.setChecked(maquina.ativo)

    def _select_tipo(self, tipo: str | None) -> None:
        """Select the machine type, keeping unknown values available."""
        if not tipo:
            return

        index = self.tipo_input.findData(tipo)
        if index < 0:
            self.tipo_input.addItem(tipo, tipo)
            index = self.tipo_input.findData(tipo)
        self.tipo_input.setCurrentIndex(index)

    def get_data(self) -> MaquinaDialogData:
        """Return normalized dialog data (hidden tariffs keep their stored value)."""
        return MaquinaDialogData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            tipo=self.tipo_input.currentData(),
            custo_hora=self._spin_to_decimal(self.custo_hora_input),
            custo_hora_serie=self._spin_to_decimal(self.custo_hora_serie_input),
            preco_ml_std=self._spin_to_decimal(self.preco_ml_std_input),
            preco_ml_serie=self._spin_to_decimal(self.preco_ml_serie_input),
            preco_lado_curto_std=self._spin_to_decimal(
                self.preco_lado_curto_std_input
            ),
            preco_lado_curto_serie=self._spin_to_decimal(
                self.preco_lado_curto_serie_input
            ),
            preco_lado_longo_std=self._spin_to_decimal(
                self.preco_lado_longo_std_input
            ),
            preco_lado_longo_serie=self._spin_to_decimal(
                self.preco_lado_longo_serie_input
            ),
            limite_lado_mm=self._spin_to_decimal(self.limite_lado_mm_input),
            custo_setup_peca_std=self._spin_to_decimal(self.custo_setup_peca_std_input),
            custo_setup_peca_serie=self._spin_to_decimal(
                self.custo_setup_peca_serie_input
            ),
            observacoes=self._empty_to_none(self.observacoes_input.text()),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting (spin boxes never raise)."""
        if not self.codigo_input.text().strip():
            self.set_error("O código é obrigatório.")
            return

        if not self.nome_input.text().strip():
            self.set_error("O nome é obrigatório.")
            return

        data = self.get_data()

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _set_spin(self, spin: QDoubleSpinBox, value: Decimal | None) -> None:
        """Load a Decimal into a spin box (None -> empty special value)."""
        if value is None:
            spin.setValue(spin.minimum())
        else:
            spin.setValue(float(value))

    def _spin_to_decimal(self, spin: QDoubleSpinBox) -> Decimal | None:
        """Return the spin box value as Decimal, or None when "not set"."""
        valor = spin.value()
        if valor < 0:
            return None

        return Decimal(str(round(valor, spin.decimals())))

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None
