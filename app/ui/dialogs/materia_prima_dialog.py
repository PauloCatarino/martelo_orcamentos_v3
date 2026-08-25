"""Dialog for creating and editing a raw material inside the V3."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.materia_prima_types import (
    FAMILIAS_VALIDAS,
    TIPO_PRECO_LIVRE,
    TIPO_PRECO_TABELA,
    TIPOS_PRECO_VALIDOS,
    UNIDADES_VALIDAS,
)
from app.domain.numeros import formatar_percentagem
from app.repositories.def_materia_prima_repository import (
    DefMateriaPrimaResumo,
    PrecoHistoricoResumo,
)
from app.ui import tema
from app.utils.formatters import format_currency

SEM_VALOR = "—"


@dataclass(frozen=True)
class MateriaPrimaDialogData:
    """Data collected by the raw material dialog."""

    descricao: str
    ref_le: str | None
    familia: str | None
    tipo: str | None
    unidade: str | None
    tipo_preco: str
    preco_tabela: Decimal | None
    desconto: Decimal | None
    margem: Decimal | None
    preco_liquido: Decimal | None
    desperdicio_percentagem: Decimal | None
    data_ultimo_preco: date | None
    comprimento: Decimal | None
    largura: Decimal | None
    espessura: Decimal | None
    coresp_orla_0_4: str | None
    coresp_orla_1_0: str | None
    cor: str | None
    fornecedor: str | None
    fornecedor_id: int | None
    nome_fabricante: str | None
    referencia_fornecedor: str | None
    ref_phc: str | None
    stock: bool | None
    ativo: bool
    observacoes: str | None


class MateriaPrimaDialog(QDialog):
    """Modal dialog for creating or editing a raw material.

    O preço líquido não se escreve: é calculado a partir do preço de tabela, do
    desconto e da margem, tal como a fórmula que o Excel tinha. Materiais de
    preço livre (PLACAS LIVRES, FERRAGEM LIVRE) não levam preço nenhum — é
    escrito dentro de cada orçamento.
    """

    HISTORICO_HEADERS = [
        "Data",
        "Preço tabela",
        "Variação",
        "Desc%",
        "Mrg%",
        "Preço líquido",
        "Origem",
        "Quem",
    ]

    def __init__(
        self,
        materia: DefMateriaPrimaResumo | None = None,
        parent=None,
        on_save: Callable[[MateriaPrimaDialogData], bool] | None = None,
        historico: list[PrecoHistoricoResumo] | None = None,
        utilizacoes: int = 0,
        ref_le_sugerida: Callable[[str], str | None] | None = None,
        fornecedores: list | None = None,
    ) -> None:
        super().__init__(parent)

        self.materia = materia
        self.on_save = on_save
        self._historico = historico or []
        self._utilizacoes = utilizacoes
        self._ref_le_sugerida = ref_le_sugerida
        self._fornecedores = fornecedores or []
        self._is_edit = materia is not None

        self.setWindowTitle(
            f"Editar matéria-prima — {materia.ref_le or materia.descricao}"
            if materia is not None
            else "Nova matéria-prima"
        )
        self.setModal(True)
        self.setMinimumSize(760, 560)

        self._criar_campos()
        self._ligar_calculo_do_preco()

        self.abas = QTabWidget()
        self.abas.addTab(self._aba_dados(), "Dados")
        self.abas.addTab(self._aba_historico(), "Histórico de preços")

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        self.error_label.setWordWrap(True)

        self.auditoria_label = QLabel(self._texto_auditoria())
        self.auditoria_label.setStyleSheet("color: #666666; font-size: 11px;")
        self.auditoria_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validar_e_aceitar)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.abas, stretch=1)
        layout.addWidget(self.error_label)
        layout.addWidget(self.auditoria_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if materia is not None:
            self._carregar(materia)
        self._atualizar_estado_preco()

    # ------------------------------------------------------------------ campos

    def _criar_campos(self) -> None:
        """Criar os campos do separador de dados."""
        self.ref_le_input = QLineEdit()
        self.ref_le_input.setToolTip(
            "Referência interna. Se deixar vazio numa matéria-prima nova, é "
            "atribuída automaticamente a partir da família (PLC, FER, ACB, ORL)."
        )
        self.descricao_input = QLineEdit()
        self.descricao_input.setToolTip("Descrição como aparece no orçamento.")

        self.familia_input = QComboBox()
        self.familia_input.addItem(SEM_VALOR, None)
        for familia in FAMILIAS_VALIDAS:
            self.familia_input.addItem(familia, familia)
        self.familia_input.setToolTip(
            "PLACAS, FERRAGENS, ACABAMENTOS ou ORLA. Manda na referência das "
            "matérias-primas novas."
        )
        self.familia_input.currentIndexChanged.connect(self._sugerir_ref_le)

        self.tipo_input = QLineEdit()
        self.tipo_input.setToolTip("Tipo dentro da família (AGLOMERADO, CORREDICAS, …).")

        self.unidade_input = QComboBox()
        self.unidade_input.addItem(SEM_VALOR, None)
        for unidade in UNIDADES_VALIDAS:
            self.unidade_input.addItem(unidade, unidade)
        self.unidade_input.setToolTip("M2 para placas e orlas, ML para barras, UND à unidade.")

        self.tipo_preco_input = QComboBox()
        for tipo_preco in TIPOS_PRECO_VALIDOS:
            self.tipo_preco_input.addItem(tipo_preco, tipo_preco)
        self.tipo_preco_input.setToolTip(
            "TABELA: o preço vem do fornecedor.\n"
            "LIVRE: material sem preço no catálogo, escrito dentro de cada "
            "orçamento (PLACAS LIVRES, FERRAGEM LIVRE)."
        )
        self.tipo_preco_input.currentIndexChanged.connect(self._atualizar_estado_preco)

        self.preco_tabela_input = QLineEdit()
        self.preco_tabela_input.setToolTip("Preço de tabela do fornecedor, antes do desconto.")
        self.desconto_input = QLineEdit()
        self.desconto_input.setToolTip("Desconto do fornecedor, em percentagem (20 = 20%).")
        self.margem_input = QLineEdit()
        self.margem_input.setToolTip("Margem a acrescentar, em percentagem.")
        self.desperdicio_input = QLineEdit()
        self.desperdicio_input.setToolTip("Desperdício previsto, em percentagem.")

        self.preco_liquido_label = QLabel(SEM_VALOR)
        self.preco_liquido_label.setStyleSheet(
            f"font-weight: bold; color: {tema.CASTANHO_ESCURO};"
        )
        self.preco_liquido_label.setToolTip(
            "Calculado: preço tabela × (1 − desconto) × (1 + margem). "
            "É este o valor que os orçamentos usam."
        )

        self.data_preco_input = QDateEdit()
        self.data_preco_input.setCalendarPopup(True)
        self.data_preco_input.setDisplayFormat("dd-MM-yyyy")
        self.data_preco_input.setSpecialValueText(SEM_VALOR)
        self.data_preco_input.setMinimumDate(QDate(2000, 1, 1))
        self.data_preco_input.setDate(self.data_preco_input.minimumDate())
        self.data_preco_input.setToolTip(
            "Quando o preço foi confirmado. Passados 12 meses, o material entra "
            "na lista dos que precisam de revisão."
        )

        self.comprimento_input = QLineEdit()
        self.largura_input = QLineEdit()
        self.espessura_input = QLineEdit()
        for campo, dica in (
            (self.comprimento_input, "Comprimento da placa (mm)."),
            (self.largura_input, "Largura da placa (mm)."),
            (self.espessura_input, "Espessura (mm)."),
        ):
            campo.setToolTip(dica)

        self.orla_0_4_input = QLineEdit()
        self.orla_0_4_input.setToolTip("Ref LE da orla fina correspondente (0,4 mm).")
        self.orla_1_0_input = QLineEdit()
        self.orla_1_0_input.setToolTip("Ref LE da orla grossa correspondente (1,0 mm).")

        self.cor_input = QLineEdit()
        self.fornecedor_input = QComboBox()
        self.fornecedor_input.addItem(SEM_VALOR, None)
        for fornecedor in self._fornecedores:
            self.fornecedor_input.addItem(fornecedor.nome, fornecedor.id)
        self.fornecedor_input.setToolTip(
            "Fornecedor do material. A lista vem do botão «Fornecedores…», que é "
            "onde se guardam os emails do pedido de preços."
        )
        self.fabricante_input = QLineEdit()
        self.referencia_fornecedor_input = QLineEdit()
        self.referencia_fornecedor_input.setToolTip(
            "Referência do artigo no fornecedor — é a que vai no pedido de preços."
        )
        self.ref_phc_input = QLineEdit()
        self.ref_phc_input.setToolTip("Referência do artigo no PHC, quando existe.")

        self.stock_input = QCheckBox("Material de stock")
        self.ativo_input = QCheckBox("Ativo")
        self.ativo_input.setChecked(True)
        self.ativo_input.setToolTip(
            "Desativar esconde o material das escolhas de linhas novas. "
            "Os orçamentos que já o usam ficam exatamente como estão."
        )

        self.observacoes_input = QTextEdit()
        self.observacoes_input.setFixedHeight(60)

    def _ligar_calculo_do_preco(self) -> None:
        """O preço líquido segue os três campos de que depende."""
        for campo in (self.preco_tabela_input, self.desconto_input, self.margem_input):
            campo.textChanged.connect(self._recalcular_preco_liquido)

    def _aba_dados(self) -> QWidget:
        """Separador com os campos do material."""
        esquerda = QFormLayout()
        esquerda.addRow("Ref LE", self.ref_le_input)
        esquerda.addRow("Descrição", self.descricao_input)
        esquerda.addRow("Família", self.familia_input)
        esquerda.addRow("Tipo", self.tipo_input)
        esquerda.addRow("Unidade", self.unidade_input)
        esquerda.addRow("Tipo de preço", self.tipo_preco_input)
        esquerda.addRow("Preço tabela", self.preco_tabela_input)
        esquerda.addRow("Desconto %", self.desconto_input)
        esquerda.addRow("Margem %", self.margem_input)
        esquerda.addRow("Preço líquido", self.preco_liquido_label)
        esquerda.addRow("Data do preço", self.data_preco_input)

        direita = QFormLayout()
        direita.addRow("Desperdício %", self.desperdicio_input)
        direita.addRow("Comprimento", self.comprimento_input)
        direita.addRow("Largura", self.largura_input)
        direita.addRow("Espessura", self.espessura_input)
        direita.addRow("Orla 0.4", self.orla_0_4_input)
        direita.addRow("Orla 1.0", self.orla_1_0_input)
        direita.addRow("Cor", self.cor_input)
        direita.addRow("Fornecedor", self.fornecedor_input)
        direita.addRow("Fabricante", self.fabricante_input)
        direita.addRow("Ref. fornecedor", self.referencia_fornecedor_input)
        direita.addRow("Ref. PHC", self.ref_phc_input)

        colunas = QHBoxLayout()
        colunas.addLayout(esquerda, stretch=1)
        colunas.addLayout(direita, stretch=1)

        marcas = QHBoxLayout()
        marcas.addWidget(self.stock_input)
        marcas.addWidget(self.ativo_input)
        marcas.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(colunas)
        layout.addLayout(marcas)
        layout.addWidget(QLabel("Observações"))
        layout.addWidget(self.observacoes_input)

        pagina = QWidget()
        pagina.setLayout(layout)
        return pagina

    def _aba_historico(self) -> QWidget:
        """Separador com o histórico de preços do material."""
        self.historico_table = QTableWidget(0, len(self.HISTORICO_HEADERS))
        self.historico_table.setHorizontalHeaderLabels(self.HISTORICO_HEADERS)
        self.historico_table.verticalHeader().setVisible(False)
        self.historico_table.setAlternatingRowColors(True)
        self.historico_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.historico_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.historico_table.horizontalHeader().setStyleSheet(
            tema.ESTILO_CABECALHO_VISTAS_DADOS
        )

        self.utilizacoes_label = QLabel(self._texto_utilizacoes())
        self.utilizacoes_label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(self.utilizacoes_label)
        layout.addWidget(self.historico_table, stretch=1)

        pagina = QWidget()
        pagina.setLayout(layout)
        self._preencher_historico()
        return pagina

    # ------------------------------------------------------------- preencher

    def _texto_auditoria(self) -> str:
        """Linha discreta com quem criou e quem alterou pela última vez."""
        if self.materia is None:
            return "Matéria-prima nova — vai ficar registada em seu nome."

        criado = self._quem_e_quando(
            self.materia.criado_por, self.materia.created_at, "Criado"
        )
        alterado = self._quem_e_quando(
            self.materia.alterado_por, self.materia.updated_at, "Última alteração"
        )
        partes = [parte for parte in (criado, alterado) if parte]
        partes.append(f"origem dos dados: {self.materia.origem_dados}")

        return " · ".join(partes)

    def _quem_e_quando(self, quem: str | None, quando, prefixo: str) -> str:
        """«Criado por paulo em 12-03-2026», ou só a data quando não há autor.

        Os materiais que vieram do Excel não têm autor: nesses, dizer «criado
        por» ninguém não ajudaria — fica só a data.
        """
        if quando is None:
            return f"{prefixo} por {quem}" if quem else ""

        data = f"{quando:%d-%m-%Y}"
        return f"{prefixo} por {quem} em {data}" if quem else f"{prefixo} em {data}"

    def _texto_utilizacoes(self) -> str:
        """Quantos orçamentos já usam este material."""
        if self._utilizacoes <= 0:
            return "Este material ainda não foi usado em nenhum orçamento."

        linhas = "linha" if self._utilizacoes == 1 else "linhas"
        return (
            f"Usado em {self._utilizacoes} {linhas} de orçamento. Alterar o preço "
            "aqui não muda nenhum desses orçamentos: cada linha guarda a cópia do "
            "preço com que foi calculada."
        )

    def _preencher_historico(self) -> None:
        """Encher a tabela do histórico, do mais recente para o mais antigo."""
        self.historico_table.setRowCount(len(self._historico))

        for linha, registo in enumerate(self._historico):
            anterior = (
                self._historico[linha + 1] if linha + 1 < len(self._historico) else None
            )
            valores = [
                self._data_do_registo(registo),
                format_currency(registo.preco_tabela),
                self._variacao(registo, anterior),
                formatar_percentagem(registo.desconto),
                formatar_percentagem(registo.margem),
                format_currency(registo.preco_liquido),
                registo.origem,
                registo.utilizador or SEM_VALOR,
            ]
            for coluna, valor in enumerate(valores):
                self.historico_table.setItem(linha, coluna, QTableWidgetItem(valor))

    def _data_do_registo(self, registo: PrecoHistoricoResumo) -> str:
        data = registo.data_preco or registo.created_at
        return f"{data:%d-%m-%Y}" if data else SEM_VALOR

    def _variacao(
        self, registo: PrecoHistoricoResumo, anterior: PrecoHistoricoResumo | None
    ) -> str:
        """Quanto o preço de tabela mudou face ao registo anterior."""
        if anterior is None or not anterior.preco_tabela or registo.preco_tabela is None:
            return SEM_VALOR

        variacao = (
            (registo.preco_tabela - anterior.preco_tabela)
            / anterior.preco_tabela
            * Decimal(100)
        )
        sinal = "+" if variacao > 0 else ""
        return f"{sinal}{variacao:.1f}%".replace(".", ",")

    def _carregar(self, materia: DefMateriaPrimaResumo) -> None:
        """Levar os valores do material para os campos."""
        self.ref_le_input.setText(materia.ref_le or "")
        self.descricao_input.setText(materia.descricao)
        self._selecionar(self.familia_input, materia.familia_original_excel)
        self.tipo_input.setText(materia.tipo_original_excel or "")
        self._selecionar(self.unidade_input, materia.unidade)
        self._selecionar(self.tipo_preco_input, materia.tipo_preco)
        self.preco_tabela_input.setText(self._texto_decimal(materia.preco_tabela))
        self.desconto_input.setText(self._texto_decimal(materia.desconto))
        self.margem_input.setText(self._texto_decimal(materia.margem))
        self.desperdicio_input.setText(
            self._texto_decimal(materia.desperdicio_percentagem)
        )
        if materia.data_ultimo_preco:
            self.data_preco_input.setDate(
                QDate(
                    materia.data_ultimo_preco.year,
                    materia.data_ultimo_preco.month,
                    materia.data_ultimo_preco.day,
                )
            )
        self.comprimento_input.setText(self._texto_decimal(materia.comprimento))
        self.largura_input.setText(self._texto_decimal(materia.largura))
        self.espessura_input.setText(self._texto_decimal(materia.espessura))
        self.orla_0_4_input.setText(materia.coresp_orla_0_4 or "")
        self.orla_1_0_input.setText(materia.coresp_orla_1_0 or "")
        self.cor_input.setText(materia.cor or "")
        self._selecionar_fornecedor(materia)
        self.fabricante_input.setText(materia.nome_fabricante or "")
        self.referencia_fornecedor_input.setText(materia.referencia_fornecedor or "")
        self.ref_phc_input.setText(materia.ref_phc or "")
        self.stock_input.setChecked(bool(materia.stock))
        self.ativo_input.setChecked(materia.ativo)
        self.observacoes_input.setPlainText(materia.observacoes or "")
        self._recalcular_preco_liquido()

    # ---------------------------------------------------------------- reações

    def _sugerir_ref_le(self) -> None:
        """Mostrar a referência que o material novo vai receber."""
        if self._is_edit or self.ref_le_input.text().strip():
            return

        familia = self.familia_input.currentData()
        if familia and self._ref_le_sugerida is not None:
            sugerida = self._ref_le_sugerida(familia)
            if sugerida:
                self.ref_le_input.setPlaceholderText(f"automática: {sugerida}")

    def _atualizar_estado_preco(self) -> None:
        """Materiais de preço livre não têm preço para escrever aqui."""
        livre = self.tipo_preco_input.currentData() == TIPO_PRECO_LIVRE
        for campo in (
            self.preco_tabela_input,
            self.desconto_input,
            self.margem_input,
        ):
            campo.setEnabled(not livre)
        self.data_preco_input.setEnabled(not livre)
        self._recalcular_preco_liquido()

    def _recalcular_preco_liquido(self) -> None:
        """Preço líquido = tabela × (1 − desconto) × (1 + margem)."""
        if self.tipo_preco_input.currentData() == TIPO_PRECO_LIVRE:
            self.preco_liquido_label.setText("preço escrito no orçamento")
            return

        preco = self._para_decimal(self.preco_tabela_input.text())
        if preco is None:
            self.preco_liquido_label.setText(SEM_VALOR)
            return

        desconto = self._para_decimal(self.desconto_input.text()) or Decimal(0)
        margem = self._para_decimal(self.margem_input.text()) or Decimal(0)
        liquido = (
            preco
            * (Decimal(1) - desconto / Decimal(100))
            * (Decimal(1) + margem / Decimal(100))
        )
        self.preco_liquido_label.setText(format_currency(liquido))

    # ----------------------------------------------------------------- gravar

    def get_data(self) -> MateriaPrimaDialogData:
        """Recolher o que está nos campos."""
        livre = self.tipo_preco_input.currentData() == TIPO_PRECO_LIVRE

        return MateriaPrimaDialogData(
            descricao=self.descricao_input.text().strip(),
            ref_le=self._texto_ou_none(self.ref_le_input.text()),
            familia=self.familia_input.currentData(),
            tipo=self._texto_ou_none(self.tipo_input.text()),
            unidade=self.unidade_input.currentData(),
            tipo_preco=self.tipo_preco_input.currentData() or TIPO_PRECO_TABELA,
            preco_tabela=None if livre else self._para_decimal(self.preco_tabela_input.text()),
            desconto=None if livre else self._para_decimal(self.desconto_input.text()),
            margem=None if livre else self._para_decimal(self.margem_input.text()),
            preco_liquido=None if livre else self._preco_liquido_calculado(),
            desperdicio_percentagem=self._para_decimal(self.desperdicio_input.text()),
            data_ultimo_preco=self._data_escolhida(),
            comprimento=self._para_decimal(self.comprimento_input.text()),
            largura=self._para_decimal(self.largura_input.text()),
            espessura=self._para_decimal(self.espessura_input.text()),
            coresp_orla_0_4=self._texto_ou_none(self.orla_0_4_input.text()),
            coresp_orla_1_0=self._texto_ou_none(self.orla_1_0_input.text()),
            cor=self._texto_ou_none(self.cor_input.text()),
            fornecedor=self._nome_do_fornecedor(),
            fornecedor_id=self.fornecedor_input.currentData(),
            nome_fabricante=self._texto_ou_none(self.fabricante_input.text()),
            referencia_fornecedor=self._texto_ou_none(
                self.referencia_fornecedor_input.text()
            ),
            ref_phc=self._texto_ou_none(self.ref_phc_input.text()),
            stock=self.stock_input.isChecked(),
            ativo=self.ativo_input.isChecked(),
            observacoes=self._texto_ou_none(self.observacoes_input.toPlainText()),
        )

    def _validar_e_aceitar(self) -> None:
        """Validar o essencial antes de gravar."""
        if not self.descricao_input.text().strip():
            self.set_error("A descrição é obrigatória.")
            return

        familia = self.familia_input.currentData()
        if not familia:
            self.set_error(
                "Escolha a família: é ela que decide a referência e o "
                "comportamento no custeio."
            )
            return

        if not self._is_edit and not self.ref_le_input.text().strip() and (
            self._ref_le_sugerida is None
        ):
            self.set_error("Indique a Ref LE.")
            return

        for campo, nome in (
            (self.preco_tabela_input, "preço de tabela"),
            (self.desconto_input, "desconto"),
            (self.margem_input, "margem"),
            (self.desperdicio_input, "desperdício"),
            (self.comprimento_input, "comprimento"),
            (self.largura_input, "largura"),
            (self.espessura_input, "espessura"),
        ):
            texto = campo.text().strip()
            if texto and self._para_decimal(texto) is None:
                self.set_error(f"O valor do {nome} não é um número válido.")
                return

        self.error_label.clear()
        if self.on_save is not None and not self.on_save(self.get_data()):
            return

        self.accept()

    def set_error(self, mensagem: str) -> None:
        """Mostrar um erro sem fechar o diálogo."""
        self.error_label.setText(mensagem)

    # ---------------------------------------------------------------- apoio

    def _preco_liquido_calculado(self) -> Decimal | None:
        """O mesmo cálculo que está no ecrã, para gravar."""
        preco = self._para_decimal(self.preco_tabela_input.text())
        if preco is None:
            return None

        desconto = self._para_decimal(self.desconto_input.text()) or Decimal(0)
        margem = self._para_decimal(self.margem_input.text()) or Decimal(0)
        return (
            preco
            * (Decimal(1) - desconto / Decimal(100))
            * (Decimal(1) + margem / Decimal(100))
        )

    def _data_escolhida(self) -> date | None:
        """Data do preço, ou None quando ficou no valor especial."""
        if not self.data_preco_input.isEnabled():
            return None

        escolhida = self.data_preco_input.date()
        if escolhida == self.data_preco_input.minimumDate():
            return None

        return date(escolhida.year(), escolhida.month(), escolhida.day())

    def _selecionar_fornecedor(self, materia: DefMateriaPrimaResumo) -> None:
        """Escolher o fornecedor pelo id; sem id, tenta pelo nome que veio do Excel."""
        indice = self.fornecedor_input.findData(materia.fornecedor_id)
        if indice < 0 and materia.fornecedor:
            indice = self.fornecedor_input.findText(materia.fornecedor.strip())

        self.fornecedor_input.setCurrentIndex(indice if indice >= 0 else 0)

    def _nome_do_fornecedor(self) -> str | None:
        """Nome do fornecedor escolhido, para acompanhar o id na linha."""
        if self.fornecedor_input.currentData() is None:
            return None

        return self.fornecedor_input.currentText().strip() or None

    def _selecionar(self, combo: QComboBox, valor: str | None) -> None:
        """Escolher um valor na lista, ou o traço quando não existe."""
        indice = combo.findData(valor)
        combo.setCurrentIndex(indice if indice >= 0 else 0)

    def _texto_ou_none(self, valor: str) -> str | None:
        texto = (valor or "").strip()
        return texto or None

    def _texto_decimal(self, valor: Decimal | None) -> str:
        """Decimal para texto, sem zeros à direita a mais."""
        if valor is None:
            return ""

        texto = f"{valor.normalize():f}" if valor == valor.to_integral_value() else f"{valor}"
        return texto.replace(".", ",")

    def _para_decimal(self, texto: str) -> Decimal | None:
        """Texto do utilizador para Decimal, aceitando vírgula decimal."""
        limpo = (texto or "").strip().replace("€", "").replace("%", "").replace(" ", "")
        if not limpo:
            return None

        try:
            return Decimal(limpo.replace(",", "."))
        except InvalidOperation:
            return None
