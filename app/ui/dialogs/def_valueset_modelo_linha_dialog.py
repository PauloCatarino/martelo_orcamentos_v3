"""Dialog for creating and editing a ValueSet model line."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaResumo
from app.ui.helpers.valueset_combo_helper import (
    carregar_chaves_valueset_combo,
    obter_valor_chave_combo,
)

ORIGEM_DADOS_OPCOES = ("MATERIA_PRIMA", "LIVRE", "EDITADO_LOCALMENTE")


@dataclass(frozen=True)
class DefValuesetModeloLinhaDialogData:
    """Data collected by the ValueSet model line dialog."""

    chave: str | None
    codigo_opcao: str
    nome_opcao: str
    ref_materia_prima: str | None
    descricao_materia_prima: str | None
    valor_texto: str | None
    padrao: bool
    ordem: int
    observacoes: str | None
    ativo: bool
    ref_le: str | None
    descricao_no_orcamento: str | None
    preco_tabela: Decimal | None
    margem_percentagem: Decimal | None
    desconto_percentagem: Decimal | None
    preco_liquido: Decimal | None
    unidade: str | None
    desperdicio_percentagem: Decimal | None
    tipo_materia_prima: str | None
    familia_materia_prima: str | None
    coresp_orla_0_4: str | None
    coresp_orla_1_0: str | None
    comp_mp: Decimal | None
    larg_mp: Decimal | None
    esp_mp: Decimal | None
    origem_dados: str | None
    editado_localmente: bool


class DefValuesetModeloLinhaDialog(QDialog):
    """Modal dialog for creating or editing a ValueSet model line."""

    def __init__(
        self,
        linha: DefValuesetModeloLinhaResumo | None = None,
        parent=None,
        on_save: Callable[[DefValuesetModeloLinhaDialogData], bool] | None = None,
    ) -> None:
        super().__init__(parent)

        self.linha = linha
        self.on_save = on_save
        self._is_edit = linha is not None

        self.setWindowTitle(
            "Editar Linha do Modelo" if self._is_edit else "Nova Linha do Modelo"
        )
        self.setModal(True)
        self.setMinimumWidth(520)

        self.chave_input = QComboBox()
        carregar_chaves_valueset_combo(
            self.chave_input,
            valor_atual=linha.chave if linha is not None else None,
        )

        self.codigo_opcao_input = QLineEdit()
        self.codigo_opcao_input.setPlaceholderText("Ex.: AGL_19_STANDARD")
        self.nome_opcao_input = QLineEdit()
        self.ref_materia_prima_input = QLineEdit()
        self.descricao_materia_prima_input = QLineEdit()
        self.valor_texto_input = QLineEdit()
        self.valor_texto_input.setPlaceholderText("Ex.: Aglomerado 19mm standard")
        self.padrao_input = QCheckBox()
        self.ordem_input = QLineEdit()
        self.ordem_input.setText("1")
        self.observacoes_input = QLineEdit()
        self.ativo_input = QCheckBox()
        self.ativo_input.setChecked(True)

        # Materia-prima snapshot fields.
        self.ref_le_input = QLineEdit()
        self.descricao_no_orcamento_input = QLineEdit()
        self.preco_tabela_input = QLineEdit()
        self.margem_input = QLineEdit()
        self.desconto_input = QLineEdit()
        self.preco_liquido_input = QLineEdit()
        self.preco_liquido_input.setPlaceholderText("Calculado a partir de preço tabela")
        self.unidade_input = QLineEdit()
        self.desperdicio_input = QLineEdit()
        self.tipo_mp_input = QLineEdit()
        self.familia_mp_input = QLineEdit()
        self.orla_0_4_input = QLineEdit()
        self.orla_1_0_input = QLineEdit()
        self.comp_mp_input = QLineEdit()
        self.larg_mp_input = QLineEdit()
        self.esp_mp_input = QLineEdit()
        self.origem_dados_input = QComboBox()
        self.origem_dados_input.setEditable(True)
        for origem in ORIGEM_DADOS_OPCOES:
            self.origem_dados_input.addItem(origem)
        self.origem_dados_input.setCurrentText("LIVRE")
        self.editado_localmente_input = QCheckBox()

        self.error_label = QLabel("")
        self.error_label.setObjectName("defValuesetModeloLinhaError")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Chave ValueSet", self.chave_input)
        form.addRow("Código opção", self.codigo_opcao_input)
        form.addRow("Nome opção", self.nome_opcao_input)
        form.addRow("Ref LE", self.ref_le_input)
        form.addRow("Descrição no orçamento", self.descricao_no_orcamento_input)
        form.addRow("Ref. matéria-prima", self.ref_materia_prima_input)
        form.addRow("Descrição matéria-prima", self.descricao_materia_prima_input)
        form.addRow("Valor texto", self.valor_texto_input)
        form.addRow("Preço tabela", self.preco_tabela_input)
        form.addRow("Margem %", self.margem_input)
        form.addRow("Desconto %", self.desconto_input)
        form.addRow("Preço líquido", self.preco_liquido_input)
        form.addRow("Unidade", self.unidade_input)
        form.addRow("Desperdício %", self.desperdicio_input)
        form.addRow("Tipo matéria-prima", self.tipo_mp_input)
        form.addRow("Família matéria-prima", self.familia_mp_input)
        form.addRow("Orla 0.4", self.orla_0_4_input)
        form.addRow("Orla 1.0", self.orla_1_0_input)
        form.addRow("Comp MP", self.comp_mp_input)
        form.addRow("Larg MP", self.larg_mp_input)
        form.addRow("Esp MP", self.esp_mp_input)
        form.addRow("Origem dados", self.origem_dados_input)
        form.addRow("Editado localmente", self.editado_localmente_input)
        form.addRow("Padrão", self.padrao_input)
        form.addRow("Ordem", self.ordem_input)
        form.addRow("Observações", self.observacoes_input)
        form.addRow("Ativo", self.ativo_input)

        form_widget = QWidget()
        form_widget.setLayout(form)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(form_widget)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(scroll, stretch=1)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if linha is not None:
            self._load_linha(linha)

    def _load_linha(self, linha: DefValuesetModeloLinhaResumo) -> None:
        """Populate the form with an existing model line."""
        self.codigo_opcao_input.setText(linha.codigo_opcao or "")
        self.nome_opcao_input.setText(linha.nome_opcao or "")
        self.ref_materia_prima_input.setText(linha.ref_materia_prima or "")
        self.descricao_materia_prima_input.setText(linha.descricao_materia_prima or "")
        self.valor_texto_input.setText(linha.valor_texto or "")
        self.padrao_input.setChecked(linha.padrao)
        self.ordem_input.setText(str(linha.ordem))
        self.observacoes_input.setText(linha.observacoes or "")
        self.ativo_input.setChecked(linha.ativo)

        self.ref_le_input.setText(linha.ref_le or "")
        self.descricao_no_orcamento_input.setText(linha.descricao_no_orcamento or "")
        self.preco_tabela_input.setText(self._format_decimal(linha.preco_tabela))
        self.margem_input.setText(self._format_decimal(linha.margem_percentagem))
        self.desconto_input.setText(self._format_decimal(linha.desconto_percentagem))
        self.preco_liquido_input.setText(self._format_decimal(linha.preco_liquido))
        self.unidade_input.setText(linha.unidade or "")
        self.desperdicio_input.setText(self._format_decimal(linha.desperdicio_percentagem))
        self.tipo_mp_input.setText(linha.tipo_materia_prima or "")
        self.familia_mp_input.setText(linha.familia_materia_prima or "")
        self.orla_0_4_input.setText(linha.coresp_orla_0_4 or "")
        self.orla_1_0_input.setText(linha.coresp_orla_1_0 or "")
        self.comp_mp_input.setText(self._format_decimal(linha.comp_mp))
        self.larg_mp_input.setText(self._format_decimal(linha.larg_mp))
        self.esp_mp_input.setText(self._format_decimal(linha.esp_mp))
        self.origem_dados_input.setCurrentText(linha.origem_dados or "")
        self.editado_localmente_input.setChecked(linha.editado_localmente)

    def get_data(self) -> DefValuesetModeloLinhaDialogData:
        """Return dialog data (raises ValueError on invalid numbers)."""
        return DefValuesetModeloLinhaDialogData(
            chave=obter_valor_chave_combo(self.chave_input),
            codigo_opcao=self.codigo_opcao_input.text().strip(),
            nome_opcao=self.nome_opcao_input.text().strip(),
            ref_materia_prima=self._empty_to_none(self.ref_materia_prima_input.text()),
            descricao_materia_prima=self._empty_to_none(
                self.descricao_materia_prima_input.text()
            ),
            valor_texto=self._empty_to_none(self.valor_texto_input.text()),
            padrao=self.padrao_input.isChecked(),
            ordem=self._parse_ordem(),
            observacoes=self._empty_to_none(self.observacoes_input.text()),
            ativo=self.ativo_input.isChecked(),
            ref_le=self._empty_to_none(self.ref_le_input.text()),
            descricao_no_orcamento=self._empty_to_none(
                self.descricao_no_orcamento_input.text()
            ),
            preco_tabela=self._parse_optional_decimal(self.preco_tabela_input, "Preço tabela"),
            margem_percentagem=self._parse_optional_decimal(self.margem_input, "Margem %"),
            desconto_percentagem=self._parse_optional_decimal(self.desconto_input, "Desconto %"),
            preco_liquido=self._parse_optional_decimal(self.preco_liquido_input, "Preço líquido"),
            unidade=self._empty_to_none(self.unidade_input.text()),
            desperdicio_percentagem=self._parse_optional_decimal(
                self.desperdicio_input, "Desperdício %"
            ),
            tipo_materia_prima=self._empty_to_none(self.tipo_mp_input.text()),
            familia_materia_prima=self._empty_to_none(self.familia_mp_input.text()),
            coresp_orla_0_4=self._empty_to_none(self.orla_0_4_input.text()),
            coresp_orla_1_0=self._empty_to_none(self.orla_1_0_input.text()),
            comp_mp=self._parse_optional_decimal(self.comp_mp_input, "Comp MP"),
            larg_mp=self._parse_optional_decimal(self.larg_mp_input, "Larg MP"),
            esp_mp=self._parse_optional_decimal(self.esp_mp_input, "Esp MP"),
            origem_dados=self._empty_to_none(self.origem_dados_input.currentText()),
            editado_localmente=self.editado_localmente_input.isChecked(),
        )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        if obter_valor_chave_combo(self.chave_input) is None:
            self.set_error("Selecione uma chave ValueSet.")
            return

        if not self.codigo_opcao_input.text().strip():
            self.set_error("O código da opção é obrigatório.")
            return

        if not self.nome_opcao_input.text().strip():
            self.set_error("O nome da opção é obrigatório.")
            return

        try:
            data = self.get_data()
        except ValueError as error:
            self.set_error(str(error))
            return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(data):
            return

        self.accept()

    def set_error(self, message: str) -> None:
        """Show a user-facing error while keeping the dialog open."""
        self.error_label.setText(message)

    def _parse_ordem(self) -> int:
        text = self.ordem_input.text().strip()
        if not text:
            return 1

        try:
            return int(text)
        except ValueError as error:
            raise ValueError("Ordem inválida. Use um número inteiro.") from error

    def _parse_optional_decimal(self, widget: QLineEdit, label: str) -> Decimal | None:
        text = widget.text().strip()
        if not text:
            return None

        normalized = text.replace(" ", "").replace("€", "").replace("%", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation as error:
            raise ValueError(f"{label} inválido. Use um número, por exemplo 1.5.") from error

    def _format_decimal(self, value: Decimal | None) -> str:
        if value is None:
            return ""

        return format(value, "f")

    def _empty_to_none(self, value: str) -> str | None:
        normalized = value.strip()
        return normalized or None
