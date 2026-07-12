"""Dialog for creating and editing a composite piece component."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

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
    POR_TOPO,
    get_dimensao_referencia_options,
    get_modo_quantidade_options,
    get_zona_aplicacao_options,
    normalize_dimensao_referencia,
)
from app.domain.associado_types import ESP as DIM_ESP
from app.domain.regra_quantidade_types import (
    FIXA,
    get_regra_quantidade_options,
    normalize_regra_quantidade,
)
from app.domain.regras_quantidade_expr import avaliar_regra_quantidade
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
    formula_comp: str | None
    formula_larg: str | None
    formula_esp: str | None
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
        self.tipo_componente_input.setToolTip(
            "Peça: outra peça do catálogo (gera sub-linha própria no custeio). "
            "Ferragem/Acessório: referência avulsa contada em UND/ML."
        )

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
        self.descricao_input.setToolTip(
            "Descrição livre do componente (mostrada nas linhas do custeio)."
        )
        self.formula_comp_input = QLineEdit()
        self.formula_larg_input = QLineEdit()
        self.formula_esp_input = QLineEdit()
        formula_tooltip = (
            "Transformação dimensional do filho. Pode usar H/L/P, HM/LM/PM e "
            "PAI_COMP/PAI_LARG/PAI_ESP. Só será aplicada ao custeio na fase seguinte."
        )
        for entrada in (
            self.formula_comp_input,
            self.formula_larg_input,
            self.formula_esp_input,
        ):
            entrada.setToolTip(formula_tooltip)

        self.ordem_input = QSpinBox()
        self.ordem_input.setRange(1, 9999)

        self.quantidade_input = QDoubleSpinBox()
        self.quantidade_input.setDecimals(3)
        self.quantidade_input.setRange(0.001, 1_000_000)
        self.quantidade_input.setValue(1)
        self.quantidade_input.setToolTip(
            "Quantidade do componente por peça principal (multiplicada pela QT "
            "da linha no custeio). Ignorada quando uma regra de quantidade "
            "estiver selecionada abaixo."
        )

        self.regra_quantidade_input = QComboBox()
        for code, label in get_regra_quantidade_options():
            self.regra_quantidade_input.addItem(label, code)
        self.regra_quantidade_input.setToolTip(
            "Critério base da quantidade: fixa, por dimensão da peça ou por "
            "topo. Para cálculo por expressão use a 'Regra de quantidade "
            "(opcional)' abaixo."
        )

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
        self.zona_aplicacao_input.setToolTip(
            "Onde o componente é aplicado na peça principal: geral, num topo "
            "específico (topo 1/topo 2), nos dois topos ou na face. Define os "
            "topos disponíveis para a quantidade por topo."
        )
        self.dimensao_referencia_input = QComboBox()
        for code, label in get_dimensao_referencia_options():
            self.dimensao_referencia_input.addItem(label, code)
        self.dimensao_referencia_input.setToolTip(
            "Dimensão da peça principal usada como MEDIDA_TOPO nas regras de "
            "quantidade (ex.: uniões nos topos usam a medida do topo onde "
            "encaixam)."
        )
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
        self.obrigatorio_input.setToolTip(
            "Marca o componente como obrigatório na definição da peça "
            "(informativo; não altera o custo)."
        )
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)
        self.ativo_input.setToolTip(
            "Só os componentes ativos entram no custeio da peça composta."
        )

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
        form.addRow("Fórmula Comp do filho", self.formula_comp_input)
        form.addRow("Fórmula Larg do filho", self.formula_larg_input)
        form.addRow("Fórmula Esp do filho", self.formula_esp_input)
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
        self.simular_button = self.button_box.addButton(
            "Simular quantidade…", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.simular_button.setToolTip(
            "Mostra a quantidade que o custeio calcularia para este associado "
            "com dimensões de exemplo da peça principal."
        )
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        self.simular_button.clicked.connect(self._abrir_simulador_quantidade)

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
        self.formula_comp_input.setText(componente.formula_comp or "")
        self.formula_larg_input.setText(componente.formula_larg or "")
        self.formula_esp_input.setText(componente.formula_esp or "")
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
            formula_comp=self._empty_to_none(self.formula_comp_input.text()),
            formula_larg=self._empty_to_none(self.formula_larg_input.text()),
            formula_esp=self._empty_to_none(self.formula_esp_input.text()),
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

    def _abrir_simulador_quantidade(self) -> None:
        """Open the quantity simulator with the form's current configuration."""
        regra_id = self.def_regra_quantidade_input.currentData()
        regra = next(
            (r for r in self._regras_disponiveis if r.id == regra_id), None
        )
        SimuladorQuantidadeAssociadoDialog(
            regra=regra,
            quantidade_fixa=Decimal(str(self.quantidade_input.value())),
            modo_quantidade=self.modo_quantidade_input.currentData() or "TOTAL",
            numero_topos=self.numero_topos_input.value(),
            dimensao_referencia=self.dimensao_referencia_input.currentData() or COMP,
            parent=self,
        ).exec()

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None


class SimuladorQuantidadeAssociadoDialog(QDialog):
    """Live simulator of an associated component's calculated quantity.

    Mirrors the costing rule exactly: the configurable expression rule (when
    selected) is evaluated with COMP/LARG/ESP/QT_PAI/MEDIDA_TOPO/NUM_TOPOS,
    otherwise the fixed quantity is used; 'Quantidade por topo' multiplies the
    result by 1 or 2 tops.
    """

    def __init__(
        self,
        *,
        regra,
        quantidade_fixa: Decimal,
        modo_quantidade: str,
        numero_topos: int,
        dimensao_referencia: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Simular quantidade do associado")
        self.setModal(True)
        self.setMinimumWidth(560)

        self._regra = regra
        self._quantidade_fixa = quantidade_fixa
        self._modo_quantidade = modo_quantidade
        self._numero_topos = numero_topos
        self._dimensao_referencia = normalize_dimensao_referencia(dimensao_referencia)

        if regra is not None:
            config = QLabel(
                f"Regra: {getattr(regra, 'codigo', '—')} — expressão "
                f"«{getattr(regra, 'expressao', '')}»"
            )
        else:
            config = QLabel(
                "Sem regra de quantidade: usa a quantidade fixa "
                f"{self._fmt(quantidade_fixa)} do formulário."
            )
        config.setWordWrap(True)

        self.comp_input = QLineEdit("2000")
        self.comp_input.setToolTip("COMP de exemplo da peça principal (mm).")
        self.larg_input = QLineEdit("600")
        self.larg_input.setToolTip("LARG de exemplo da peça principal (mm).")
        self.esp_input = QLineEdit("19")
        self.esp_input.setToolTip("ESP de exemplo da peça principal (mm).")
        self.qt_pai_input = QLineEdit("1")
        self.qt_pai_input.setToolTip("QT_PAI: quantidade da peça principal.")

        self.resultado = QLabel("")
        self.resultado.setWordWrap(True)

        form = QFormLayout()
        form.addRow("COMP peça principal (mm)", self.comp_input)
        form.addRow("LARG peça principal (mm)", self.larg_input)
        form.addRow("ESP peça principal (mm)", self.esp_input)
        form.addRow("QT peça principal", self.qt_pai_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Fechar")
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(lambda _button: self.accept())

        layout = QVBoxLayout(self)
        layout.addWidget(config)
        layout.addLayout(form)
        layout.addWidget(self.resultado)
        layout.addWidget(buttons)

        for widget in (
            self.comp_input,
            self.larg_input,
            self.esp_input,
            self.qt_pai_input,
        ):
            widget.textChanged.connect(self._recalcular)
        self._recalcular()

    def _recalcular(self) -> None:
        comp = self._parse(self.comp_input.text())
        larg = self._parse(self.larg_input.text())
        esp = self._parse(self.esp_input.text())
        qt_pai = self._parse(self.qt_pai_input.text()) or Decimal("1")

        medida_topo = self._medida_topo(comp, larg, esp)
        linhas = [
            f"MEDIDA_TOPO ({self._dimensao_referencia}) = "
            f"{self._fmt(medida_topo) if medida_topo is not None else '—'} mm; "
            f"NUM_TOPOS = {self._numero_topos}"
        ]

        if self._regra is None:
            base = self._quantidade_fixa
            linhas.append(f"Quantidade fixa = {self._fmt(base)}")
        else:
            contexto = {
                "COMP": comp,
                "LARG": larg,
                "ESP": esp,
                "QT_PAI": qt_pai,
                "MEDIDA_TOPO": medida_topo,
                "NUM_TOPOS": self._numero_topos,
            }
            quantidade, motivo = avaliar_regra_quantidade(
                getattr(self._regra, "expressao", None), contexto
            )
            if motivo is not None:
                linhas.append(f"Regra não calculada: {motivo}")
                self.resultado.setText("\n".join(linhas))
                return
            base = Decimal(quantidade)
            linhas.append(f"Resultado da expressão = {self._fmt(base)}")

        if self._modo_quantidade == POR_TOPO:
            if self._numero_topos not in (1, 2):
                linhas.append(
                    "Quantidade por topo exige 1 ou 2 topos — corrija o "
                    "'Número de topos'."
                )
                self.resultado.setText("\n".join(linhas))
                return
            total = base * Decimal(self._numero_topos)
            linhas.append(
                f"Quantidade por topo × {self._numero_topos} topo(s) = "
                f"{self._fmt(total)}"
            )
        else:
            total = base

        linhas.append(
            f"Quantidade do associado por peça principal (qt_und) = {self._fmt(total)}"
        )
        self.resultado.setText("\n".join(linhas))

    def _medida_topo(self, comp, larg, esp):
        """Resolve MEDIDA_TOPO like the costing (COMP/ESP explicit; else LARG)."""
        if self._dimensao_referencia == COMP:
            return comp
        if self._dimensao_referencia == DIM_ESP:
            return esp
        # LARG and MEDIDA_TOPO (the short end) both map to LARG.
        return larg

    @staticmethod
    def _parse(text: str) -> Decimal | None:
        try:
            return Decimal(text.strip().replace(",", ".")) if text.strip() else None
        except InvalidOperation:
            return None

    @staticmethod
    def _fmt(valor: Decimal | None) -> str:
        if valor is None:
            return ""
        normalized = valor.normalize()
        if normalized == normalized.to_integral_value():
            normalized = normalized.quantize(Decimal("1"))
        return format(normalized, "f").replace(".", ",")
