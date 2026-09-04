"""Dialog to insert/edit a manual-operation cost line (phase 8S.3)."""

from __future__ import annotations
from app.ui import tema

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from app.domain.custo_producao import calcular_custo_por_minutos, escolher_tarifa
from app.domain.producao_types import TIPO_PRODUCAO_SERIE, normalize_tipo_producao
from app.repositories.def_maquina_repository import DefMaquinaResumo
from app.utils.formatters import format_currency, format_quantity
from app.ui.widgets.combo_sem_scroll import ComboSemScroll, SpinDuploSemScroll, SpinSemScroll


@dataclass(frozen=True)
class OperacaoManualDialogData:
    """Data collected by the manual-operation dialog."""

    descricao: str
    def_maquina_id: int | None
    tempo_minutos: Decimal
    quantidade: Decimal


class OperacaoManualDialog(QDialog):
    """Modal dialog to add or edit a user-defined manual-operation line.

    The cost is computed from the chosen machine's effective STD/SERIE hourly
    rate ((minutes / 60) × custo_hora); the user defines the description and
    minutes. Machines of type MANUAL, MONTAGEM, EMBALAMENTO or CNC are offered.
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
        tipo_producao: str | None = None,
    ) -> None:
        super().__init__(parent)

        self.on_save = on_save
        self._is_edit = descricao is not None
        self._tipo_producao = normalize_tipo_producao(tipo_producao) or "STD"
        self._usar_serie = self._tipo_producao == TIPO_PRODUCAO_SERIE

        self.setWindowTitle(
            "Editar Operação Manual" if self._is_edit else "Inserir Operação Manual"
        )
        self.setModal(True)
        self.setMinimumWidth(440)

        self.descricao_input = QLineEdit(descricao or "")
        self.descricao_input.setPlaceholderText("Ex.: cortar perfis de alumínio")
        self.descricao_input.setToolTip(
            "Descrição que ficará visível na linha de custeio."
        )

        self.maquina_input = ComboSemScroll()
        self._custo_hora_por_maquina = {
            m.id: escolher_tarifa(
                m.custo_hora, m.custo_hora_serie, self._usar_serie
            )[0]
            for m in maquinas
        }
        indice_manual = -1
        for posicao, maquina in enumerate(maquinas):
            self.maquina_input.addItem(f"{maquina.codigo} - {maquina.nome}", maquina.id)
            if indice_manual < 0 and (maquina.tipo or "").upper() == "MANUAL":
                indice_manual = posicao
        if indice_manual >= 0:
            self.maquina_input.setCurrentIndex(indice_manual)
        self.maquina_input.setToolTip(
            "Máquina/centro de custo. A tarifa horária segue o tipo de produção "
            "do item (SERIE usa STD como fallback quando necessário)."
        )

        self.tempo_input = SpinDuploSemScroll()
        self.tempo_input.setDecimals(2)
        self.tempo_input.setRange(0.0, 9_999_999.0)
        self.tempo_input.setSuffix(" min")
        self.tempo_input.setToolTip(
            "Minutos necessários para UMA unidade. Ex.: 0,1 min = 6 segundos."
        )

        self.quantidade_input = SpinSemScroll()
        self.quantidade_input.setRange(1, 9999)
        self.quantidade_input.setValue(1)
        self.quantidade_input.setToolTip(
            "Quantidade da linha. Ao inserir, começa em QT = 1."
        )

        self.error_label = QLabel("")
        self.error_label.setObjectName("operacaoManualDialogError")
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        self.error_label.setWordWrap(True)

        self.aviso_label = QLabel("")
        self.aviso_label.setObjectName("operacaoManualDialogAviso")
        self.aviso_label.setStyleSheet(f"color: {tema.TEXTO_AVISO};")
        self.aviso_label.setWordWrap(True)

        info = QLabel(
            "Trabalho avulso (manual, montagem, embalamento ou CNC). Indique "
            "o tempo de UMA unidade; o Martelo multiplica-o pela quantidade."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666666; font-size: 11px;")

        form = QFormLayout()
        form.addRow("Descrição", self.descricao_input)
        form.addRow("Máquina", self.maquina_input)
        form.addRow("Tempo por unidade", self.tempo_input)
        form.addRow("Quantidade", self.quantidade_input)

        self.resumo_label = QLabel("")
        self.resumo_label.setObjectName("operacaoManualDialogResumo")
        self.resumo_label.setWordWrap(True)
        self.resumo_label.setStyleSheet(
            "background-color: #f1f5f9; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 8px; color: #0f172a;"
        )

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setToolTip(
            "Inserir/atualizar a linha com o custo apresentado no resumo."
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setToolTip(
            "Fechar sem guardar alterações."
        )
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(form)
        layout.addWidget(self.resumo_label)
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

        self.maquina_input.currentIndexChanged.connect(self._atualizar_previsao)
        self.tempo_input.valueChanged.connect(self._atualizar_previsao)
        self.quantidade_input.valueChanged.connect(self._atualizar_previsao)
        self._atualizar_previsao()

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
        """Warn (without blocking) when the selected hourly rate is missing."""
        maquina_id = self.maquina_input.currentData()
        if maquina_id is None:
            self.aviso_label.clear()
            return
        if self._custo_hora_por_maquina.get(maquina_id) is None:
            self.aviso_label.setText(
                f"Aviso: esta máquina não tem custo/hora {self._tipo_producao} "
                "nem uma tarifa STD de fallback — o custo "
                "ficará por calcular (Configurações → Máquinas)."
            )
        else:
            self.aviso_label.clear()

    def _atualizar_previsao(self) -> None:
        """Show unit and current-total cost with the same formula as costing."""
        self._atualizar_aviso_custo_hora()
        tarifa = self._custo_hora_por_maquina.get(self.maquina_input.currentData())
        minutos_unitarios = Decimal(str(round(self.tempo_input.value(), 2)))
        qt = Decimal(str(self.quantidade_input.value()))
        tempo_total = minutos_unitarios * qt
        custo_unitario = calcular_custo_por_minutos(minutos_unitarios, tarifa)
        custo_total = calcular_custo_por_minutos(tempo_total, tarifa)

        tarifa_texto = (
            f"{format_currency(tarifa)}/h" if tarifa is not None else "não definida"
        )
        custo_unitario_texto = (
            format_currency(custo_unitario)
            if custo_unitario is not None
            else "por calcular"
        )
        custo_total_texto = (
            format_currency(custo_total) if custo_total is not None else "por calcular"
        )
        total = (
            f"<br><b>Total para QT {format_quantity(qt)}: "
            f"{custo_total_texto}</b> — {format_quantity(tempo_total)} min"
            if qt != Decimal("1")
            else ""
        )
        self.resumo_label.setText(
            f"<b>Previsão para QT = 1 · tarifa {self._tipo_producao}</b>"
            f"<span style='font-size: 17px; color: #075985;'>"
            f" &nbsp; <b>{custo_unitario_texto}</b></span><br>"
            f"{format_quantity(minutos_unitarios)} min/un × {tarifa_texto} ÷ 60"
            f"{total}"
        )

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)
