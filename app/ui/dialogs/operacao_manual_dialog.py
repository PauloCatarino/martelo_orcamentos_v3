"""Dialog to insert/edit a manual-operation cost line (phase 8S.3)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.repositories.def_maquina_repository import DefMaquinaResumo


@dataclass(frozen=True)
class OperacaoManualDialogData:
    """Data collected by the manual-operation dialog."""

    descricao: str
    def_maquina_id: int | None
    tempo_minutos: Decimal
    quantidade: Decimal


class OperacaoManualDialog(QDialog):
    """Modal dialog to add or edit a user-defined manual-operation line.

    The cost is computed from the chosen machine's STD hourly rate
    ((minutes / 60) × custo_hora); the user defines the description and minutes.
    Machines of type MANUAL, MONTAGEM, EMBALAMENTO or CNC are offered.
    """

    def __init__(
        self,
        maquinas: list[DefMaquinaResumo],
        descricao: str | None = None,
        def_maquina_id: int | None = None,
        tempo_minutos: Decimal | None = None,
        quantidade: Decimal | None = None,
        parent=None,
        on_save: Callable[[OperacaoManualDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.on_save = on_save
        self._is_edit = descricao is not None

        self.setWindowTitle(
            "Editar Operação Manual" if self._is_edit else "Inserir Operação Manual"
        )
        self.setModal(True)
        self.setMinimumWidth(440)

        self.descricao_input = QLineEdit(descricao or "")
        self.descricao_input.setPlaceholderText("Ex.: cortar perfis de alumínio")

        self.maquina_input = QComboBox()
        self._custo_hora_por_maquina = {m.id: m.custo_hora for m in maquinas}
        indice_manual = -1
        for posicao, maquina in enumerate(maquinas):
            self.maquina_input.addItem(f"{maquina.codigo} - {maquina.nome}", maquina.id)
            if indice_manual < 0 and (maquina.tipo or "").upper() == "MANUAL":
                indice_manual = posicao
        if indice_manual >= 0:
            self.maquina_input.setCurrentIndex(indice_manual)

        self.tempo_input = QDoubleSpinBox()
        self.tempo_input.setDecimals(2)
        self.tempo_input.setRange(0.0, 9_999_999.0)
        self.tempo_input.setSuffix(" min")

        self.quantidade_input = QSpinBox()
        self.quantidade_input.setRange(1, 9999)
        self.quantidade_input.setValue(1)

        self.error_label = QLabel("")
        self.error_label.setObjectName("operacaoManualDialogError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        self.aviso_label = QLabel("")
        self.aviso_label.setObjectName("operacaoManualDialogAviso")
        self.aviso_label.setStyleSheet("color: #b36b00;")
        self.aviso_label.setWordWrap(True)

        info = QLabel(
            "Trabalho avulso (manual, montagem, embalamento ou CNC). "
            "O custo = (tempo total / 60) × custo/hora STD da máquina. "
            "Tempo total = tempo × quantidade."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666666; font-size: 11px;")

        form = QFormLayout()
        form.addRow("Descrição", self.descricao_input)
        form.addRow("Máquina", self.maquina_input)
        form.addRow("Tempo", self.tempo_input)
        form.addRow("Quantidade", self.quantidade_input)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(form)
        layout.addWidget(self.aviso_label)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if def_maquina_id is not None:
            indice = self.maquina_input.findData(def_maquina_id)
            if indice >= 0:
                self.maquina_input.setCurrentIndex(indice)
        if tempo_minutos is not None and quantidade:
            self.tempo_input.setValue(float(tempo_minutos) / float(quantidade))
        elif tempo_minutos is not None:
            self.tempo_input.setValue(float(tempo_minutos))
        if quantidade is not None:
            self.quantidade_input.setValue(int(quantidade))

        self.maquina_input.currentIndexChanged.connect(self._atualizar_aviso_custo_hora)
        self._atualizar_aviso_custo_hora()

    def get_data(self) -> OperacaoManualDialogData:
        """Return normalized dialog data."""
        return OperacaoManualDialogData(
            descricao=self.descricao_input.text().strip(),
            def_maquina_id=self.maquina_input.currentData(),
            tempo_minutos=Decimal(str(round(self.tempo_input.value(), 2))),
            quantidade=Decimal(str(self.quantidade_input.value())),
        )

    def _validate_and_accept(self) -> None:
        """Validate the required fields before accepting."""
        if not self.descricao_input.text().strip():
            self.set_error("A descrição é obrigatória.")
            return
        if self.tempo_input.value() <= 0:
            self.set_error("Indique o tempo em minutos (maior que 0).")
            return
        if self.maquina_input.currentData() is None:
            self.set_error("Selecione uma máquina.")
            return

        data = self.get_data()
        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def _atualizar_aviso_custo_hora(self) -> None:
        """Warn (without blocking) when the chosen machine has no STD hourly rate."""
        maquina_id = self.maquina_input.currentData()
        if maquina_id is None:
            self.aviso_label.clear()
            return
        if self._custo_hora_por_maquina.get(maquina_id) is None:
            self.aviso_label.setText(
                "Aviso: esta máquina não tem custo/hora STD definido — o custo "
                "ficará por calcular (Configurações → Máquinas)."
            )
        else:
            self.aviso_label.clear()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)
