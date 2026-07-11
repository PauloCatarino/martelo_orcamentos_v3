"""Dialog for creating and editing a composite piece component."""

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
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.domain.componente_types import (
    PECA,
    get_componente_type_options,
    normalize_componente_type,
)
from app.domain.associado_types import (
    COMP,
    GERAL,
    get_dimensao_referencia_options,
    get_modo_quantidade_options,
    get_zona_aplicacao_options,
)
from app.domain.regra_quantidade_types import (
    FIXA,
    get_regra_quantidade_options,
    normalize_regra_quantidade,
)
from app.repositories.def_peca_componente_repository import DefPecaComponenteResumo
from app.repositories.def_peca_repository import DefPecaResumo


TOOLTIP_REGRA_QUANTIDADE = (
    "Regra (expressão) que calcula a quantidade deste componente a partir das "
    "dimensões da peça principal "
    "(COMP/LARG/ESP/QT_PAI/MEDIDA_TOPO/NUM_TOPOS) no custeio.\n"
    "Com uma regra selecionada, a quantidade é calculada automaticamente; "
    "«— sem regra —» mantém a quantidade fixa acima como valor manual."
)


@dataclass(frozen=True)
class DefPecaComponenteDialogData:
    """Data collected by the component dialog."""

    tipo_componente: str
    def_peca_componente_id: int | None
    referencia_componente: str | None
    descricao: str | None
    ordem: int
    quantidade: Decimal
    regra_quantidade: str
    def_regra_quantidade_id: int | None
    zona_aplicacao: str
    dimensao_referencia: str
    numero_topos: int
    modo_quantidade: str
    prioridade_valueset: int
    obrigatorio: bool
    ativo: bool


class DefPecaComponenteDialog(QDialog):
    """Modal dialog for creating or editing a composite piece component."""

    def __init__(
        self,
        pecas_disponiveis: list[DefPecaResumo],
        componente: DefPecaComponenteResumo | None = None,
        parent=None,
        on_save: Callable[[DefPecaComponenteDialogData], bool] | None = None,
        regras_disponiveis: list | None = None,
    ) -> None:
        super().__init__(parent)

        self.componente = componente
        self.on_save = on_save
        self._is_edit = componente is not None
        self._pecas_disponiveis = list(pecas_disponiveis)
        self._regras_disponiveis = list(regras_disponiveis or [])

        self.setWindowTitle("Editar Associado" if self._is_edit else "Novo Associado")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.tipo_componente_input = QComboBox()
        for code, label in get_componente_type_options():
            self.tipo_componente_input.addItem(label, code)

        self.peca_componente_input = QComboBox()
        for peca in pecas_disponiveis:
            self.peca_componente_input.addItem(f"{peca.codigo} - {peca.nome}", peca.id)

        self.referencia_input = QLineEdit()
        self.selecionar_ref_button = QPushButton("Selecionar...")
        self.selecionar_ref_button.clicked.connect(self.selecionar_referencia)

        self.referencia_row = QWidget()
        referencia_row_layout = QHBoxLayout()
        referencia_row_layout.setContentsMargins(0, 0, 0, 0)
        referencia_row_layout.addWidget(self.referencia_input, stretch=1)
        referencia_row_layout.addWidget(self.selecionar_ref_button)
        self.referencia_row.setLayout(referencia_row_layout)

        self.descricao_input = QLineEdit()

        self.ordem_input = QSpinBox()
        self.ordem_input.setRange(1, 9999)

        self.quantidade_input = QDoubleSpinBox()
        self.quantidade_input.setDecimals(3)
        self.quantidade_input.setRange(0.001, 1_000_000)
        self.quantidade_input.setValue(1)

        self.regra_quantidade_input = QComboBox()
        for code, label in get_regra_quantidade_options():
            self.regra_quantidade_input.addItem(label, code)

        # Configurable quantity rule (phase 8T.5.1): "— sem regra —" + active rules.
        self.def_regra_quantidade_input = QComboBox()
        self.def_regra_quantidade_input.setToolTip(TOOLTIP_REGRA_QUANTIDADE)
        self.def_regra_quantidade_input.addItem("— sem regra —", None)
        for regra in self._regras_disponiveis:
            self.def_regra_quantidade_input.addItem(
                f"{regra.codigo} — {regra.nome}", regra.id
            )

        self.zona_aplicacao_input = QComboBox()
        for code, label in get_zona_aplicacao_options():
            self.zona_aplicacao_input.addItem(label, code)
        self.dimensao_referencia_input = QComboBox()
        for code, label in get_dimensao_referencia_options():
            self.dimensao_referencia_input.addItem(label, code)
        self.numero_topos_input = QSpinBox()
        self.numero_topos_input.setRange(0, 2)
        self.numero_topos_input.setToolTip(
            "0 = não aplicável; 1 = um topo; 2 = dois topos. "
            "Só multiplica quando a aplicação escolhida for 'Quantidade por topo'."
        )
        self.modo_quantidade_input = QComboBox()
        for code, label in get_modo_quantidade_options():
            self.modo_quantidade_input.addItem(label, code)
        self.modo_quantidade_input.setToolTip(
            "Quantidade total: o resultado da regra já é o total da peça. "
            "Quantidade por topo: o resultado é multiplicado por 1 ou 2 topos."
        )

        self.prioridade_valueset_input = QSpinBox()
        self.prioridade_valueset_input.setRange(1, 999)
        self.prioridade_valueset_input.setValue(1)
        self.prioridade_valueset_input.setToolTip(
            "Seleciona exatamente a opção desta prioridade na chave ValueSet "
            "do componente. Não existe substituição automática pela prioridade 1 "
            "quando a prioridade escolhida estiver vazia."
        )

        self.obrigatorio_input = QCheckBox()
        self.obrigatorio_input.setChecked(True)
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        self.error_label = QLabel("")
        self.error_label.setObjectName("defPecaComponenteError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        self.peca_componente_label = QLabel("Peça componente")
        self.referencia_label = QLabel("Referência componente")
        self.ordem_label = QLabel("Ordem")

        self.tipo_hint_label = QLabel()
        self.tipo_hint_label.setObjectName("defPecaComponenteTipoHint")
        self.tipo_hint_label.setWordWrap(True)
        self.tipo_hint_label.setStyleSheet("color: #666666; font-size: 11px;")

        form = QFormLayout()
        form.addRow("Tipo de componente", self.tipo_componente_input)
        form.addRow(self.peca_componente_label, self.peca_componente_input)
        form.addRow(self.referencia_label, self.referencia_row)
        form.addRow(self.tipo_hint_label)
        form.addRow("Descrição", self.descricao_input)
        form.addRow(self.ordem_label, self.ordem_input)
        form.addRow("Quantidade", self.quantidade_input)
        form.addRow("Regra quantidade", self.regra_quantidade_input)
        regra_label = QLabel("Regra de quantidade (opcional)")
        regra_label.setToolTip(TOOLTIP_REGRA_QUANTIDADE)
        form.addRow(regra_label, self.def_regra_quantidade_input)
        form.addRow("Zona de aplicação", self.zona_aplicacao_input)
        form.addRow("Dimensão de referência", self.dimensao_referencia_input)
        form.addRow("Número de topos", self.numero_topos_input)
        form.addRow("Aplicação da quantidade", self.modo_quantidade_input)
        form.addRow("Prioridade ValueSet", self.prioridade_valueset_input)
        form.addRow("Obrigatório", self.obrigatorio_input)
        form.addRow("Ativo", self.ativo_input)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.tipo_componente_input.currentIndexChanged.connect(self._update_tipo_fields)

        if componente is not None:
            self._load_componente(componente)
        else:
            self.ordem_label.setVisible(False)
            self.ordem_input.setVisible(False)

        self._update_tipo_fields()

    def _load_componente(self, componente: DefPecaComponenteResumo) -> None:
        """Populate the form with an existing component."""
        self._select_combo_data(
            self.tipo_componente_input,
            normalize_componente_type(componente.tipo_componente),
        )
        if componente.def_peca_componente_id is not None:
            self._select_combo_data(
                self.peca_componente_input, componente.def_peca_componente_id
            )
        self.referencia_input.setText(componente.referencia_componente or "")
        self.descricao_input.setText(componente.descricao or "")
        self.ordem_input.setValue(componente.ordem)
        self.quantidade_input.setValue(float(componente.quantidade))
        self._select_combo_data(
            self.regra_quantidade_input,
            normalize_regra_quantidade(componente.regra_quantidade),
        )
        if componente.def_regra_quantidade_id is not None:
            self._select_combo_data(
                self.def_regra_quantidade_input, componente.def_regra_quantidade_id
            )
        self._select_combo_data(self.zona_aplicacao_input, componente.zona_aplicacao)
        self._select_combo_data(
            self.dimensao_referencia_input, componente.dimensao_referencia
        )
        self.numero_topos_input.setValue(componente.numero_topos)
        self._select_combo_data(
            self.modo_quantidade_input, componente.modo_quantidade
        )
        self.prioridade_valueset_input.setValue(
            getattr(componente, "prioridade_valueset", 1) or 1
        )
        self.obrigatorio_input.setChecked(componente.obrigatorio)
        self.ativo_input.setChecked(componente.ativo)

    def _update_tipo_fields(self) -> None:
        """Show the piece picker or the textual reference based on the type."""
        is_peca = self.tipo_componente_input.currentData() == PECA
        self.peca_componente_label.setVisible(is_peca)
        self.peca_componente_input.setVisible(is_peca)
        self.referencia_label.setVisible(not is_peca)
        self.referencia_row.setVisible(not is_peca)

        if is_peca:
            self.tipo_hint_label.setText("Selecione uma peça existente da biblioteca.")
        else:
            self.tipo_hint_label.setText(
                "Selecione uma referência existente ou escreva manualmente."
            )

    def selecionar_referencia(self) -> None:
        """Pick an existing reference (DefPeca code) for a non-piece component."""
        if not self._pecas_disponiveis:
            self.set_error("Não há referências disponíveis para selecionar.")
            return

        opcoes = {
            f"{peca.codigo} - {peca.nome}": peca.codigo
            for peca in self._pecas_disponiveis
            if peca.codigo
        }
        if not opcoes:
            self.set_error("Não há referências disponíveis para selecionar.")
            return

        escolha, confirmado = QInputDialog.getItem(
            self,
            "Selecionar referência",
            "Referência do componente:",
            list(opcoes.keys()),
            0,
            False,
        )
        if confirmado and escolha:
            self.error_label.clear()
            self.referencia_input.setText(opcoes[escolha])

    def _select_combo_data(self, combo: QComboBox, value: object) -> None:
        """Select the combo entry matching value when present."""
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def get_data(self) -> DefPecaComponenteDialogData:
        """Return normalized dialog data."""
        tipo = self.tipo_componente_input.currentData() or PECA
        is_peca = tipo == PECA
        return DefPecaComponenteDialogData(
            tipo_componente=tipo,
            def_peca_componente_id=self.peca_componente_input.currentData() if is_peca else None,
            referencia_componente=(
                None if is_peca else self._empty_to_none(self.referencia_input.text())
            ),
            descricao=self._empty_to_none(self.descricao_input.text()),
            ordem=self.ordem_input.value(),
            quantidade=Decimal(str(self.quantidade_input.value())),
            regra_quantidade=self.regra_quantidade_input.currentData() or FIXA,
            def_regra_quantidade_id=self.def_regra_quantidade_input.currentData(),
            zona_aplicacao=self.zona_aplicacao_input.currentData() or GERAL,
            dimensao_referencia=self.dimensao_referencia_input.currentData() or COMP,
            numero_topos=self.numero_topos_input.value(),
            modo_quantidade=self.modo_quantidade_input.currentData() or "TOTAL",
            prioridade_valueset=self.prioridade_valueset_input.value(),
            obrigatorio=self.obrigatorio_input.isChecked(),
            ativo=self.ativo_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate the component before accepting."""
        data = self.get_data()

        if data.tipo_componente == PECA and not data.def_peca_componente_id:
            self.error_label.setText("Escolha a peça componente.")
            return

        if (
            data.tipo_componente != PECA
            and not data.referencia_componente
            and not data.descricao
        ):
            self.error_label.setText("Indique a referência ou a descrição do componente.")
            return

        if data.quantidade <= 0:
            self.error_label.setText("A quantidade deve ser maior que 0.")
            return

        if data.modo_quantidade == "POR_TOPO" and data.numero_topos == 0:
            self.error_label.setText(
                "Na quantidade por topo, indique 1 ou 2 no número de topos."
            )
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None
