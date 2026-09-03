"""Dialog for creating and editing a raw material inside the V3."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.materia_prima_types import (
    FAMILIAS_VALIDAS,
    PAPEIS_COMPONENTE_VALIDOS,
    PAPEL_PRINCIPAL,
    PAPEL_SECUNDARIO,
    TIPO_PRECO_LIVRE,
    TIPO_PRECO_TABELA,
    TIPOS_PRECO_VALIDOS,
    UNIDADES_VALIDAS,
)
from app.domain.numeros import formatar_percentagem
from app.repositories.def_materia_prima_componente_repository import (
    ComponenteDados,
    ComponenteResumo,
)
from app.repositories.def_materia_prima_repository import (
    DefMateriaPrimaResumo,
    PrecoHistoricoResumo,
)
from app.ui import tema
from app.utils.formatters import format_currency

SEM_VALOR = "\u2014"

#: Lado maior da imagem do material na ficha, em pixeis. Grande o
#: suficiente para se ver a peca, pequeno o suficiente para nao empurrar
#: os campos para fora do ecra.
LADO_IMAGEM = 190


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
    link: str | None
    imagem_ficheiro: str | None
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

    #: As colunas do separador Componentes. As tres chaves da ponte ao iMos
    #: aparecem pela ordem em que a importacao as tenta.
    COMPONENTES_HEADERS = [
        "Papel",
        "Descrição",
        "Qt/conj.",
        "Nome iMos",
        "Ref PHC",
        "Ref Fornecedor",
    ]
    COMPONENTES_LARGURAS = {
        "Papel": 122,
        "Descrição": 240,
        "Qt/conj.": 70,
        "Nome iMos": 230,
        "Ref PHC": 90,
        "Ref Fornecedor": 150,
    }

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
        on_save_as: Callable[[MateriaPrimaDialogData], bool] | None = None,
        historico: list[PrecoHistoricoResumo] | None = None,
        utilizacoes: int = 0,
        ref_le_sugerida: Callable[[str], str | None] | None = None,
        fornecedores: list | None = None,
        pasta_imagens: str | None = None,
        componentes: list[ComponenteResumo] | None = None,
    ) -> None:
        super().__init__(parent)

        self.materia = materia
        self.on_save = on_save
        self.on_save_as = on_save_as
        self._historico = historico or []
        self._utilizacoes = utilizacoes
        self._ref_le_sugerida = ref_le_sugerida
        self._fornecedores = fornecedores or []
        self._pasta_imagens = (pasta_imagens or "").strip()
        self._componentes_iniciais = componentes or []
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
        self.abas.addTab(self._aba_componentes(), "Componentes")
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
        self.save_as_button = self.button_box.addButton(
            "Gravar como…", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.save_as_button.setToolTip(
            "Grava estes dados como uma matéria-prima nova, sem alterar a "
            "original. A referência é atribuída automaticamente."
        )
        self.save_as_button.setVisible(self._is_edit)
        self.save_as_button.clicked.connect(self._validar_e_gravar_como)
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
        self._mostrar_imagem()

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

        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("https://…")
        self.link_input.setToolTip(
            "Morada na net onde se vê este material: a página do fabricante, a "
            "foto do fornecedor, o PDF do sistema.\n"
            "É opcional — a maioria dos materiais não tem link nenhum."
        )
        self.abrir_link_button = QPushButton("Abrir")
        self.abrir_link_button.setToolTip(
            "Abrir este link no browser. Confirme sempre a morada antes de abrir."
        )
        self.abrir_link_button.clicked.connect(self._abrir_link)

        # A imagem do material: o IMOS guarda o NOME do ficheiro na ficha do
        # artigo ("Preview Image") e os ficheiros vivem todos na mesma pasta da
        # biblioteca. Aqui guarda-se o mesmo nome, e a pasta e' a configuracao
        # `pasta_imagens_imos`.
        self.imagem_input = QLineEdit()
        self.imagem_input.setPlaceholderText("HF_637.76.352_PE_AXILO_72_92.JPG")
        self.imagem_input.setToolTip(
            "Nome do ficheiro da imagem, como vem no «Preview Image» do iMos.\n"
            "A pasta onde ele vive define-se em Configurações → Caminhos do "
            "Sistema («pasta_imagens_imos»).\n"
            "É opcional — sem imagem a ficha funciona na mesma."
        )
        self.imagem_input.textChanged.connect(self._mostrar_imagem)

        self.imagem_label = QLabel()
        self.imagem_label.setFixedSize(LADO_IMAGEM, LADO_IMAGEM)
        self.imagem_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imagem_label.setWordWrap(True)
        self.imagem_label.setStyleSheet(
            f"border: 1px solid {tema.CINZA_CASTANHO}; border-radius: 4px;"
            f" background-color: #FFFFFF; color: {tema.CINZA_ESCURO};"
            " font-size: 11px; padding: 6px;"
        )

        self.procurar_imagem_button = QPushButton("Procurar…")
        self.procurar_imagem_button.setToolTip(
            "Escolher a imagem na biblioteca do iMos. Fica guardado só o nome "
            "do ficheiro, não o caminho todo."
        )
        self.procurar_imagem_button.clicked.connect(self._procurar_imagem)
        # Ligar o sinal depois do botao existir, e correr uma vez a seguir: com
        # o campo vazio o botao nasce desligado.
        self.link_input.textChanged.connect(self._atualizar_botao_link)
        self._atualizar_botao_link()

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

        # A imagem fica a` direita dos campos, com o nome do ficheiro por baixo:
        # quem abre a ficha ve' logo a peca de que se trata, sem ler nada.
        coluna_imagem = QVBoxLayout()
        coluna_imagem.setSpacing(6)
        titulo_imagem = QLabel("Imagem")
        titulo_imagem.setStyleSheet(f"color: {tema.CASTANHO_MEDIO}; font-size: 11px;")
        coluna_imagem.addWidget(titulo_imagem)
        coluna_imagem.addWidget(self.imagem_label)
        coluna_imagem.addWidget(self.imagem_input)
        coluna_imagem.addWidget(self.procurar_imagem_button)
        coluna_imagem.addStretch()

        colunas = QHBoxLayout()
        colunas.addLayout(esquerda, stretch=1)
        colunas.addLayout(direita, stretch=1)
        colunas.addLayout(coluna_imagem)

        marcas = QHBoxLayout()
        marcas.addWidget(self.stock_input)
        marcas.addWidget(self.ativo_input)
        marcas.addStretch()

        # O link ocupa a largura toda: uma morada de catálogo não cabe em meia
        # linha, e cortada não se percebe para onde vai.
        linha_link = QHBoxLayout()
        linha_link.addWidget(QLabel("Link"))
        linha_link.addWidget(self.link_input, stretch=1)
        linha_link.addWidget(self.abrir_link_button)

        layout = QVBoxLayout()
        layout.addLayout(colunas)
        layout.addLayout(linha_link)
        layout.addLayout(marcas)
        layout.addWidget(QLabel("Observações"))
        layout.addWidget(self.observacoes_input)

        pagina = QWidget()
        pagina.setLayout(layout)
        return pagina

    def _aba_componentes(self) -> QWidget:
        """Separador com os componentes (filhos) deste conjunto.

        O Martelo orça uma ferragem como UM todo; o iMos exporta a mesma obra
        desmontada, uma linha por componente. Esta tabela é o mapa entre as
        duas coisas — e é ela que permite avaliar uma obra desenhada aos preços
        do catálogo.
        """
        explicacao = QLabel(
            "Para as ferragens que o Martelo orça como um conjunto (dobradiça "
            "de copo + calço, pé + base). Cada linha é um componente, com as "
            "referências por onde ele aparece nas listas do iMos.\n"
            "O PRINCIPAL é quem conta os conjuntos — pode haver mais do que um "
            "(dois pés de alturas diferentes que valem o mesmo Ref LE). Os "
            "SECUNDARIO só conferem, e podem repetir-se noutros conjuntos.\n"
            "O preço fica sempre nesta matéria-prima: isto é um mapa de "
            "referências, não uma segunda forma de calcular o preço."
        )
        explicacao.setWordWrap(True)
        explicacao.setStyleSheet(f"color: {tema.CASTANHO_MEDIO}; font-size: 11px;")

        self.componentes_table = QTableWidget(0, len(self.COMPONENTES_HEADERS))
        self.componentes_table.setHorizontalHeaderLabels(self.COMPONENTES_HEADERS)
        self.componentes_table.verticalHeader().setVisible(False)
        self.componentes_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.componentes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        for indice, cabecalho in enumerate(self.COMPONENTES_HEADERS):
            self.componentes_table.setColumnWidth(
                indice, self.COMPONENTES_LARGURAS.get(cabecalho, 110)
            )
        self.componentes_table.setToolTip(
            "Duplo clique numa célula para escrever. As três referências são "
            "tentadas por esta ordem: nome iMos, Ref PHC, Ref Fornecedor."
        )

        self.add_componente_button = QPushButton("+ Componente")
        self.add_componente_button.setToolTip(
            "Acrescentar uma linha. Nasce SECUNDARIO — só quem manda na "
            "contagem se declara principal."
        )
        self.add_componente_button.clicked.connect(
            lambda: self._acrescentar_componente()
        )

        self.remover_componente_button = QPushButton("Eliminar linha")
        self.remover_componente_button.setToolTip(
            "Eliminar o componente escolhido. Só é gravado ao carregar em "
            "«Guardar»."
        )
        self.remover_componente_button.clicked.connect(self._remover_componente)

        botoes = QHBoxLayout()
        botoes.addWidget(self.add_componente_button)
        botoes.addWidget(self.remover_componente_button)
        botoes.addStretch()

        self.componentes_status = QLabel("")
        self.componentes_status.setStyleSheet(
            f"color: {tema.CASTANHO_MEDIO}; font-size: 11px;"
        )
        self.componentes_status.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(explicacao)
        layout.addLayout(botoes)
        layout.addWidget(self.componentes_table, stretch=1)
        layout.addWidget(self.componentes_status)

        pagina = QWidget()
        pagina.setLayout(layout)

        for componente in self._componentes_iniciais:
            self._acrescentar_componente(componente)
        self._descrever_componentes()
        return pagina

    def _acrescentar_componente(
        self, componente: ComponenteResumo | None = None
    ) -> None:
        """Uma linha nova na tabela dos componentes."""
        linha = self.componentes_table.rowCount()
        self.componentes_table.insertRow(linha)

        papel = QComboBox()
        for valor in PAPEIS_COMPONENTE_VALIDOS:
            papel.addItem(valor, valor)
        papel.setCurrentText(
            componente.papel if componente is not None else PAPEL_SECUNDARIO
        )
        papel.setToolTip(
            "PRINCIPAL conta os conjuntos; SECUNDARIO só confere e pode "
            "repetir-se noutros conjuntos."
        )
        papel.currentIndexChanged.connect(self._descrever_componentes)
        self.componentes_table.setCellWidget(linha, 0, papel)

        if componente is None:
            valores = ("", "1", "", "", "")
        else:
            valores = (
                componente.descricao or "",
                self._texto_decimal(componente.quantidade),
                componente.nome_imos or "",
                componente.ref_phc or "",
                componente.ref_fornecedor or "",
            )
        for deslocamento, valor in enumerate(valores, start=1):
            self.componentes_table.setItem(
                linha, deslocamento, QTableWidgetItem(valor)
            )

        self._descrever_componentes()

    def _remover_componente(self) -> None:
        linha = self.componentes_table.currentRow()
        if linha < 0:
            self.componentes_status.setText(
                "Escolha primeiro a linha que quer eliminar."
            )
            return
        self.componentes_table.removeRow(linha)
        self._descrever_componentes()

    def _descrever_componentes(self) -> None:
        """A linha de apoio: quantos são e quantos contam."""
        total = self.componentes_table.rowCount()
        if not total:
            self.componentes_status.setText(
                "Sem componentes. Uma ferragem simples não precisa de nenhum — "
                "nesse caso basta escrever o nome do artigo do iMos no "
                "separador Dados."
            )
            return
        principais = sum(
            1
            for linha in range(total)
            if self._papel_da_linha(linha) == PAPEL_PRINCIPAL
        )
        aviso = ""
        if principais == 0:
            aviso = (
                "  —  sem nenhum PRINCIPAL este conjunto nunca vai ser contado "
                "numa obra."
            )
        self.componentes_status.setText(
            f"{total} componente{'s' if total != 1 else ''}, "
            f"{principais} principa{'is' if principais != 1 else 'l'}.{aviso}"
        )

    def _papel_da_linha(self, linha: int) -> str:
        widget = self.componentes_table.cellWidget(linha, 0)
        if widget is None:
            return PAPEL_SECUNDARIO
        return widget.currentData() or PAPEL_SECUNDARIO

    def _celula_componente(self, linha: int, coluna: int) -> str:
        item = self.componentes_table.item(linha, coluna)
        return (item.text() if item is not None else "").strip()

    def componentes(self) -> list[ComponenteDados]:
        """Os componentes tal como estão na tabela, prontos a gravar."""
        linhas: list[ComponenteDados] = []
        for linha in range(self.componentes_table.rowCount()):
            quantidade = self._para_decimal(self._celula_componente(linha, 2))
            linhas.append(
                ComponenteDados(
                    papel=self._papel_da_linha(linha),
                    descricao=self._celula_componente(linha, 1) or None,
                    quantidade=quantidade if quantidade is not None else Decimal("1"),
                    nome_imos=self._celula_componente(linha, 3) or None,
                    ref_phc=self._celula_componente(linha, 4) or None,
                    ref_fornecedor=self._celula_componente(linha, 5) or None,
                    ordem=linha + 1,
                )
            )
        return linhas

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
        self.link_input.setText(materia.link or "")
        self.imagem_input.setText(materia.imagem_ficheiro or "")
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
            link=self._texto_ou_none(self.link_input.text()),
            imagem_ficheiro=self._texto_ou_none(self.imagem_input.text()),
            stock=self.stock_input.isChecked(),
            ativo=self.ativo_input.isChecked(),
            observacoes=self._texto_ou_none(self.observacoes_input.toPlainText()),
        )

    def _validar_e_gravar_como(self) -> None:
        """Gravar os dados do ecrã como uma matéria-prima nova.

        A Ref LE é limpa de propósito: o registo novo recebe a próxima livre da
        família, para nunca haver duas matérias-primas com a mesma referência.
        """
        self._validar_e_aceitar(gravar_como=True)

    def _validar_e_aceitar(self, gravar_como: bool = False) -> None:
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
        dados = self.get_data()
        if gravar_como:
            dados = replace(dados, ref_le=None)
            if self.on_save_as is not None and not self.on_save_as(dados):
                return
        elif self.on_save is not None and not self.on_save(dados):
            return

        self.accept()

    def _atualizar_botao_link(self) -> None:
        """O «Abrir» só liga quando há mesmo uma morada escrita."""
        self.abrir_link_button.setEnabled(bool(self.link_input.text().strip()))

    def _abrir_link(self) -> None:
        """Abrir o link no browser do sistema."""
        morada = self.link_input.text().strip()
        if not morada:
            return
        url = QUrl.fromUserInput(morada)
        if not url.isValid() or not QDesktopServices.openUrl(url):
            self.set_error(
                "Não foi possível abrir este link. Confirme que a morada está "
                "completa (começa por «https://»)."
            )

    def _caminho_da_imagem(self) -> Path | None:
        """O ficheiro da imagem, juntando a pasta configurada ao nome escrito."""
        nome = self.imagem_input.text().strip()
        if not nome or not self._pasta_imagens:
            return None
        return Path(self._pasta_imagens) / nome

    def _mostrar_imagem(self) -> None:
        """Desenhar a imagem — ou dizer, sem rodeios, porque não há nenhuma.

        A pasta é uma unidade de rede: quando ela não responde, a ficha não
        pode ficar com um quadrado vazio a fingir que o material não tem
        imagem. Diz-se o que se passa.
        """
        nome = self.imagem_input.text().strip()
        if not nome:
            self.imagem_label.setPixmap(QPixmap())
            self.imagem_label.setText("Sem imagem")
            return

        if not self._pasta_imagens:
            self.imagem_label.setPixmap(QPixmap())
            self.imagem_label.setText(
                "Falta configurar a pasta das imagens do iMos em "
                "Configurações → Caminhos do Sistema."
            )
            return

        caminho = self._caminho_da_imagem()
        pixmap = QPixmap(str(caminho)) if caminho is not None else QPixmap()
        if pixmap.isNull():
            self.imagem_label.setPixmap(QPixmap())
            self.imagem_label.setText(f"Não foi encontrada a imagem\n«{nome}».")
            return

        self.imagem_label.setText("")
        self.imagem_label.setPixmap(
            pixmap.scaled(
                LADO_IMAGEM - 8,
                LADO_IMAGEM - 8,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _procurar_imagem(self) -> None:
        """Escolher a imagem na biblioteca do iMos; guarda só o nome."""
        pasta = self._pasta_imagens or ""
        escolhido, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher a imagem do material",
            pasta,
            "Imagens (*.jpg *.jpeg *.png *.gif *.bmp);;Todos os ficheiros (*)",
        )
        if not escolhido:
            return
        self.imagem_input.setText(Path(escolhido).name)

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
        """Escolher o fornecedor pelo id; sem id, tenta pelo nome que veio do Excel.

        O ``findData`` só é usado quando há mesmo um id: com ``None`` ele casa
        com o traço da primeira linha e o nome nunca chegava a ser tentado.
        """
        indice = -1
        if materia.fornecedor_id is not None:
            indice = self.fornecedor_input.findData(materia.fornecedor_id)

        if indice < 0 and materia.fornecedor:
            indice = self.fornecedor_input.findText(
                materia.fornecedor.strip(), Qt.MatchFlag.MatchFixedString
            )

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
