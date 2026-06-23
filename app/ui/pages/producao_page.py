"""Production process list and detail page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.datas import normalizar_data
from app.domain.producao_estados import ESTADOS_PRODUCAO
from app.models.producao import Producao
from app.services.producao_service import (
    ProducaoService,
    converter_orcamento,
    filtrar_processos,
)
from app.ui import tema
from app.ui.dialogs.converter_orcamento_dialog import ConverterOrcamentoDialog
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.estado_splitter import ligar_persistencia_splitter
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


TIPOS_PASTA_PRODUCAO = (
    "Encomenda de Cliente",
    "Encomenda de Cliente Final",
)


class ProducaoPage(QWidget):
    """Production process page with an editable V3 detail form."""

    TABLE_HEADERS = [
        "Ano",
        "Processo",
        "Estado",
        "Cliente",
        "Ref Cliente",
        "Obra",
        "Localização",
        "Nº Enc PHC",
        "V. Obra",
        "V. CutRite",
        "Data Início",
        "Data Entrega",
        "Responsável",
        "Tipo Pasta",
    ]
    COLUMN_WIDTHS = {
        "Ano": 60,
        "Processo": 115,
        "Estado": 110,
        "Cliente": 190,
        "Ref Cliente": 110,
        "Obra": 210,
        "Localização": 150,
        "Nº Enc PHC": 95,
        "V. Obra": 75,
        "V. CutRite": 80,
        "Data Início": 95,
        "Data Entrega": 95,
        "Responsável": 120,
        "Tipo Pasta": 170,
    }
    CENTERED_HEADERS = {
        "Ano",
        "Processo",
        "Estado",
        "Nº Enc PHC",
        "V. Obra",
        "V. CutRite",
        "Data Início",
        "Data Entrega",
    }

    def __init__(self) -> None:
        super().__init__()

        self._todos: list[Producao] = []
        self._processos_by_row: dict[int, Producao] = {}
        self._selected_processo_id: int | None = None
        self._dirty = False
        self._a_preencher_form = False

        self.cabecalho = BarraCabecalho(
            "Produção",
            ["Obras em produção do Martelo V3"],
        )

        self.convert_button = QPushButton("Converter Orçamento")
        self.convert_button.setToolTip("Converter um orçamento adjudicado numa obra de produção")
        self.convert_button.clicked.connect(self._converter_orcamento)

        self.save_button = QPushButton("Salvar")
        self.save_button.setToolTip("Gravar as alterações da obra selecionada")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setToolTip("Recarregar a lista de obras")
        self.refresh_button.clicked.connect(self.carregar_processos)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.convert_button)
        actions_layout.addWidget(self.save_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.campo_pesquisa = CampoPesquisa()
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)
        self.campo_pesquisa.limpar_clicado.connect(self._limpar_filtros)

        self.estado_combo = QComboBox()
        self.cliente_combo = QComboBox()
        self.responsavel_combo = QComboBox()
        for combo in (self.estado_combo, self.cliente_combo, self.responsavel_combo):
            combo.currentTextChanged.connect(self._render)

        filters_layout = QHBoxLayout()
        filters_layout.addWidget(self.campo_pesquisa)
        filters_layout.addWidget(QLabel("Estado"))
        filters_layout.addWidget(self.estado_combo)
        filters_layout.addWidget(QLabel("Cliente"))
        filters_layout.addWidget(self.cliente_combo)
        filters_layout.addWidget(QLabel("Responsável"))
        filters_layout.addWidget(self.responsavel_combo)
        filters_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("producaoStatus")

        self.detail_panel = self._criar_painel_detalhe()

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        self._aplicar_larguras_colunas()
        self.table.itemSelectionChanged.connect(self._on_select_row)
        ligar_persistencia_larguras(self.table, "producao")

        self.footer_label = QLabel("")
        self.footer_label.setObjectName("producaoFooter")
        self.footer_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(6)
        table_layout.addWidget(self.table, stretch=1)
        table_layout.addWidget(self.footer_label)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.detail_panel)
        self.splitter.addWidget(table_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        if not ligar_persistencia_splitter(self.splitter, "producao"):
            self.splitter.setSizes([330, 520])

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
        layout.addLayout(filters_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.splitter, stretch=1)

        self.setLayout(layout)
        self.carregar_processos()

    def _criar_painel_detalhe(self) -> QScrollArea:
        grupo = QGroupBox("Detalhe da obra")
        grupo.setStyleSheet(
            f"QGroupBox {{ color: {tema.CASTANHO_ESCURO}; font-weight: bold; }}"
        )

        self.processo_input = self._readonly_line()
        self.ano_input = self._readonly_line()
        self.num_enc_phc_input = self._readonly_line()
        self.versao_obra_input = self._readonly_line()
        self.versao_plano_input = self._readonly_line()
        self.cliente_input = self._readonly_line()
        self.cliente_simplex_input = self._readonly_line()
        self.num_cliente_phc_input = self._readonly_line()
        self.num_orcamento_input = self._readonly_line()
        self.versao_orc_input = self._readonly_line()
        self.preco_total_input = self._readonly_line()
        self.qt_artigos_input = self._readonly_line()

        self.estado_form_combo = QComboBox()
        self.estado_form_combo.addItems(ESTADOS_PRODUCAO)

        self.responsavel_form_combo = QComboBox()
        self.responsavel_form_combo.setEditable(True)

        self.ref_cliente_input = QLineEdit()
        self.obra_input = QLineEdit()
        self.localizacao_input = QLineEdit()
        self.data_inicio_input = QLineEdit()
        self.data_inicio_input.setPlaceholderText("dd-mm-aaaa")
        self.data_entrega_input = QLineEdit()
        self.data_entrega_input.setPlaceholderText("dd-mm-aaaa")

        self.tipo_pasta_combo = QComboBox()
        self.tipo_pasta_combo.addItems(TIPOS_PASTA_PRODUCAO)

        dados_grid = QGridLayout()
        dados_grid.setHorizontalSpacing(8)
        dados_grid.setVerticalSpacing(6)
        campos = [
            ("Processo", self.processo_input),
            ("Ano", self.ano_input),
            ("Nº Enc PHC", self.num_enc_phc_input),
            ("V. Obra", self.versao_obra_input),
            ("V. CutRite", self.versao_plano_input),
            ("Cliente", self.cliente_input),
            ("Cliente simplex", self.cliente_simplex_input),
            ("Nº Cliente PHC", self.num_cliente_phc_input),
            ("Nº Orçamento", self.num_orcamento_input),
            ("V. Orç", self.versao_orc_input),
            ("Preço total", self.preco_total_input),
            ("Qt artigos", self.qt_artigos_input),
            ("Estado", self.estado_form_combo),
            ("Responsável", self.responsavel_form_combo),
            ("Ref Cliente", self.ref_cliente_input),
            ("Obra", self.obra_input),
            ("Localização", self.localizacao_input),
            ("Data Início", self.data_inicio_input),
            ("Data Entrega", self.data_entrega_input),
            ("Tipo Pasta", self.tipo_pasta_combo),
        ]
        for index, (label, widget) in enumerate(campos):
            self._add_grid_field(dados_grid, index // 4, index % 4, label, widget)

        self.descricao_artigos_text = self._text_edit()
        self.materias_usados_text = self._text_edit()
        self.descricao_producao_text = self._text_edit()
        self.notas1_text = self._text_edit()
        self.notas2_text = self._text_edit()
        self.notas3_text = self._text_edit()

        textos_grid = QGridLayout()
        textos_grid.setHorizontalSpacing(8)
        textos_grid.setVerticalSpacing(6)
        textos = [
            ("Descrição artigos", self.descricao_artigos_text),
            ("Matérias usados", self.materias_usados_text),
            ("Descrição produção", self.descricao_producao_text),
            ("Notas 1", self.notas1_text),
            ("Notas 2", self.notas2_text),
            ("Notas 3", self.notas3_text),
        ]
        for index, (label, widget) in enumerate(textos):
            row = (index // 3) * 2
            col = index % 3
            textos_grid.addWidget(QLabel(label), row, col)
            textos_grid.addWidget(widget, row + 1, col)

        layout = QVBoxLayout(grupo)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(10)
        layout.addLayout(dados_grid)
        layout.addLayout(textos_grid)

        self._readonly_widgets = [
            self.processo_input,
            self.ano_input,
            self.num_enc_phc_input,
            self.versao_obra_input,
            self.versao_plano_input,
            self.cliente_input,
            self.cliente_simplex_input,
            self.num_cliente_phc_input,
            self.num_orcamento_input,
            self.versao_orc_input,
            self.preco_total_input,
            self.qt_artigos_input,
        ]
        self._editable_widgets = [
            self.estado_form_combo,
            self.responsavel_form_combo,
            self.ref_cliente_input,
            self.obra_input,
            self.localizacao_input,
            self.data_inicio_input,
            self.data_entrega_input,
            self.tipo_pasta_combo,
            self.descricao_artigos_text,
            self.materias_usados_text,
            self.descricao_producao_text,
            self.notas1_text,
            self.notas2_text,
            self.notas3_text,
        ]
        self._aplicar_tooltips_editaveis()
        self._ligar_sinais_edicao()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grupo)
        scroll.setMinimumHeight(240)
        return scroll

    def _readonly_line(self) -> QLineEdit:
        line = QLineEdit()
        line.setReadOnly(True)
        line.setStyleSheet(
            f"background-color: {tema.BEGE_AREIA}; color: {tema.CASTANHO_ESCURO};"
        )
        return line

    def _text_edit(self) -> QTextEdit:
        text_edit = QTextEdit()
        text_edit.setAcceptRichText(False)
        text_edit.setMinimumHeight(70)
        return text_edit

    def _add_grid_field(
        self,
        grid: QGridLayout,
        row: int,
        pair_col: int,
        label: str,
        widget: QWidget,
    ) -> None:
        col = pair_col * 2
        grid.addWidget(QLabel(label), row, col)
        grid.addWidget(widget, row, col + 1)

    def _ligar_sinais_edicao(self) -> None:
        for line_edit in (
            self.ref_cliente_input,
            self.obra_input,
            self.localizacao_input,
            self.data_inicio_input,
            self.data_entrega_input,
        ):
            line_edit.textChanged.connect(self._on_user_edit)
        for combo in (
            self.estado_form_combo,
            self.responsavel_form_combo,
            self.tipo_pasta_combo,
        ):
            combo.currentTextChanged.connect(self._on_user_edit)
        for text_edit in (
            self.descricao_artigos_text,
            self.materias_usados_text,
            self.descricao_producao_text,
            self.notas1_text,
            self.notas2_text,
            self.notas3_text,
        ):
            text_edit.textChanged.connect(self._on_user_edit)

    def _aplicar_tooltips_editaveis(self) -> None:
        self.estado_form_combo.setToolTip("Estado da obra em produção")
        self.responsavel_form_combo.setToolTip("Responsável pela obra")
        self.ref_cliente_input.setToolTip("Referência do cliente")
        self.obra_input.setToolTip("Nome ou descrição curta da obra")
        self.localizacao_input.setToolTip("Localização da obra")
        self.data_inicio_input.setToolTip("Data no formato dd-mm-aaaa")
        self.data_entrega_input.setToolTip("Data no formato dd-mm-aaaa")
        self.tipo_pasta_combo.setToolTip("Pasta de destino no servidor")
        self.descricao_artigos_text.setToolTip("Descrição dos artigos da obra")
        self.materias_usados_text.setToolTip("Matérias usadas na obra")
        self.descricao_producao_text.setToolTip("Descrição da produção")
        self.notas1_text.setToolTip("Notas adicionais da obra")
        self.notas2_text.setToolTip("Notas adicionais da obra")
        self.notas3_text.setToolTip("Notas adicionais da obra")

    def carregar_processos(self, selecionar_id: int | None = None) -> None:
        """Load production processes into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                processos = ProducaoService(session).listar_processos()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar a producao.")
            return

        self._todos = list(processos)
        if selecionar_id is not None:
            self._selected_processo_id = selecionar_id
        self._atualizar_filtros()
        self._render()

        if not self._todos:
            self.status_label.setText("Sem processos de produção para mostrar.")

    def _render(self, *_args) -> None:
        """Render the in-memory list using the current search and filters."""
        selected_id = self._selected_processo_id
        filtrados = filtrar_processos(
            self._todos,
            texto=self.campo_pesquisa.texto(),
            estado=self._combo_valor(self.estado_combo),
            cliente=self._combo_valor(self.cliente_combo),
            responsavel=self._combo_valor(self.responsavel_combo),
        )
        self._preencher_tabela(filtrados)
        self.footer_label.setText(f"{len(filtrados)} de {len(self._todos)}")
        self._restaurar_selecao_apos_render(selected_id)

    def _limpar_filtros(self) -> None:
        """Clear search and reset all filters to 'Todos'."""
        widgets = (
            self.campo_pesquisa,
            self.estado_combo,
            self.cliente_combo,
            self.responsavel_combo,
        )
        estados_sinais = [(widget, widget.blockSignals(True)) for widget in widgets]
        self.campo_pesquisa.limpar()
        for combo in (self.estado_combo, self.cliente_combo, self.responsavel_combo):
            if combo.count():
                combo.setCurrentIndex(0)
        for widget, estado_anterior in estados_sinais:
            widget.blockSignals(estado_anterior)
        self._render()

    def _atualizar_filtros(self) -> None:
        """Populate filter combos from the loaded list, preserving selection."""
        self._popular_combo(
            self.estado_combo,
            self._combinar_valores(list(ESTADOS_PRODUCAO), self._valores_distintos("estado")),
        )
        self._popular_combo(
            self.cliente_combo,
            self._valores_distintos("nome_cliente"),
        )
        responsaveis = self._valores_distintos("responsavel")
        self._popular_combo(self.responsavel_combo, responsaveis)
        self._popular_responsaveis_form(responsaveis)

    def _popular_combo(self, combo: QComboBox, valores: list[str]) -> None:
        atual = combo.currentText() or "Todos"
        estado_anterior = combo.blockSignals(True)
        combo.clear()
        combo.addItem("Todos")
        for valor in valores:
            combo.addItem(valor)

        indice = combo.findText(atual)
        combo.setCurrentIndex(indice if indice >= 0 else 0)
        combo.blockSignals(estado_anterior)

    def _popular_responsaveis_form(self, valores: list[str]) -> None:
        atual = self.responsavel_form_combo.currentText()
        estado_anterior = self.responsavel_form_combo.blockSignals(True)
        self.responsavel_form_combo.clear()
        self.responsavel_form_combo.addItem("")
        for valor in valores:
            self.responsavel_form_combo.addItem(valor)
        self.responsavel_form_combo.setCurrentText(atual)
        self.responsavel_form_combo.blockSignals(estado_anterior)

    def _valores_distintos(self, atributo: str) -> list[str]:
        valores = {
            str(valor).strip()
            for valor in (
                getattr(processo, atributo, None) for processo in self._todos
            )
            if valor is not None and str(valor).strip()
        }
        return sorted(valores, key=str.lower)

    @staticmethod
    def _combinar_valores(primeiros: list[str], restantes: list[str]) -> list[str]:
        valores: list[str] = []
        vistos: set[str] = set()
        for valor in [*primeiros, *restantes]:
            chave = valor.strip().lower()
            if not chave or chave in vistos:
                continue
            valores.append(valor)
            vistos.add(chave)
        return valores

    @staticmethod
    def _combo_valor(combo: QComboBox) -> str | None:
        valor = combo.currentText().strip()
        if not valor or valor == "Todos":
            return None
        return valor

    def _preencher_tabela(self, processos: list[Producao]) -> None:
        """Fill the table with production processes."""
        self._processos_by_row = {}
        estado_sinais = self.table.blockSignals(True)
        self.table.setRowCount(len(processos))

        for row_index, processo in enumerate(processos):
            self._processos_by_row[row_index] = processo
            values = [
                processo.ano,
                processo.codigo_processo,
                processo.estado or "",
                processo.nome_cliente or "",
                processo.ref_cliente or "",
                processo.obra or "",
                processo.localizacao or "",
                processo.num_enc_phc,
                processo.versao_obra,
                processo.versao_plano,
                normalizar_data(processo.data_inicio),
                normalizar_data(processo.data_entrega),
                processo.responsavel or "",
                processo.tipo_pasta or "",
            ]

            for column_index, value in enumerate(values):
                header = self.TABLE_HEADERS[column_index]
                item = self._criar_item_tabela(self._format_value(value), header)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, {"producao_id": processo.id})
                self.table.setItem(row_index, column_index, item)

        self.table.blockSignals(estado_sinais)

    def _criar_item_tabela(self, value: str, header: str) -> QTableWidgetItem:
        """Create a table item with the list page alignment conventions."""
        item = QTableWidgetItem(value)
        if header in self.CENTERED_HEADERS:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        if value:
            item.setToolTip(value)
        return item

    def _restaurar_selecao_apos_render(self, selected_id: int | None) -> None:
        if selected_id is not None and self._selecionar_processo_id(selected_id):
            if not self._dirty:
                processo = self._processo_visivel_por_id(selected_id)
                if processo is not None:
                    self._fill_form(processo)
            return

        if self._dirty:
            return

        if self._processos_by_row:
            processo = self._processos_by_row[min(self._processos_by_row)]
            self._selecionar_processo_id(processo.id)
            self._fill_form(processo)
        else:
            self._clear_form()

    def _on_select_row(self) -> None:
        row = self.table.currentRow()
        processo = self._processos_by_row.get(row)
        if processo is None:
            return

        if self._selected_processo_id == processo.id:
            return

        if self._dirty:
            resposta = QMessageBox.question(
                self,
                "Alterações por gravar",
                "Há alterações por gravar. Descartar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                if self._selected_processo_id is not None:
                    self._selecionar_processo_id(self._selected_processo_id)
                return
            self._set_dirty(False)

        self._fill_form(processo)

    def _fill_form(self, proc: Producao) -> None:
        """Fill detail widgets from one production process without marking dirty."""
        self._a_preencher_form = True
        estados = self._bloquear_sinais_form()
        try:
            self.processo_input.setText(self._format_value(proc.codigo_processo))
            self.ano_input.setText(self._format_value(proc.ano))
            self.num_enc_phc_input.setText(self._format_value(proc.num_enc_phc))
            self.versao_obra_input.setText(self._format_value(proc.versao_obra))
            self.versao_plano_input.setText(self._format_value(proc.versao_plano))
            self.cliente_input.setText(self._format_value(proc.nome_cliente))
            self.cliente_simplex_input.setText(
                self._format_value(proc.nome_cliente_simplex)
            )
            self.num_cliente_phc_input.setText(self._format_value(proc.num_cliente_phc))
            self.num_orcamento_input.setText(self._format_value(proc.num_orcamento))
            self.versao_orc_input.setText(self._format_value(proc.versao_orc))
            self.preco_total_input.setText(self._format_value(proc.preco_total))
            self.qt_artigos_input.setText(self._format_value(proc.qt_artigos))

            self._set_combo_text(self.estado_form_combo, proc.estado)
            self._set_combo_text(self.responsavel_form_combo, proc.responsavel)
            self.ref_cliente_input.setText(self._format_value(proc.ref_cliente))
            self.obra_input.setText(self._format_value(proc.obra))
            self.localizacao_input.setText(self._format_value(proc.localizacao))
            self.data_inicio_input.setText(normalizar_data(proc.data_inicio))
            self.data_entrega_input.setText(normalizar_data(proc.data_entrega))
            self._set_combo_text(self.tipo_pasta_combo, proc.tipo_pasta)
            self.descricao_artigos_text.setPlainText(
                self._format_value(proc.descricao_artigos)
            )
            self.materias_usados_text.setPlainText(
                self._format_value(proc.materias_usados)
            )
            self.descricao_producao_text.setPlainText(
                self._format_value(proc.descricao_producao)
            )
            self.notas1_text.setPlainText(self._format_value(proc.notas1))
            self.notas2_text.setPlainText(self._format_value(proc.notas2))
            self.notas3_text.setPlainText(self._format_value(proc.notas3))
            self._selected_processo_id = proc.id
        finally:
            self._restaurar_sinais_form(estados)
            self._a_preencher_form = False
        self._set_dirty(False)

    def _clear_form(self) -> None:
        estados = self._bloquear_sinais_form()
        try:
            for line in self._readonly_widgets:
                line.clear()
            for widget in self._editable_widgets:
                if isinstance(widget, QLineEdit):
                    widget.clear()
                elif isinstance(widget, QTextEdit):
                    widget.clear()
                elif isinstance(widget, QComboBox):
                    widget.setCurrentIndex(-1)
            self._selected_processo_id = None
        finally:
            self._restaurar_sinais_form(estados)
        self._set_dirty(False)

    def _collect_form(self) -> dict:
        """Collect editable fields from the detail form."""
        return {
            "estado": self.estado_form_combo.currentText().strip(),
            "responsavel": self._none_if_empty(
                self.responsavel_form_combo.currentText()
            ),
            "ref_cliente": self._none_if_empty(self.ref_cliente_input.text()),
            "obra": self._none_if_empty(self.obra_input.text()),
            "localizacao": self._none_if_empty(self.localizacao_input.text()),
            "data_inicio": normalizar_data(self.data_inicio_input.text()),
            "data_entrega": normalizar_data(self.data_entrega_input.text()),
            "tipo_pasta": self.tipo_pasta_combo.currentText().strip(),
            "descricao_artigos": self._none_if_empty(
                self.descricao_artigos_text.toPlainText()
            ),
            "materias_usados": self._none_if_empty(
                self.materias_usados_text.toPlainText()
            ),
            "descricao_producao": self._none_if_empty(
                self.descricao_producao_text.toPlainText()
            ),
            "notas1": self._none_if_empty(self.notas1_text.toPlainText()),
            "notas2": self._none_if_empty(self.notas2_text.toPlainText()),
            "notas3": self._none_if_empty(self.notas3_text.toPlainText()),
        }

    def _save(self) -> None:
        """Persist the selected production process edits."""
        if self._selected_processo_id is None:
            self.status_label.setText("Selecione uma obra de produção.")
            return

        data = self._collect_form()
        if data["estado"] not in ESTADOS_PRODUCAO:
            self.status_label.setText("Estado de produção inválido.")
            return
        if data["tipo_pasta"] not in TIPOS_PASTA_PRODUCAO:
            self.status_label.setText("Tipo de pasta inválido.")
            return

        updated_by_id = (
            app_session.current_user.id
            if app_session.current_user is not None
            else None
        )
        proc_id = self._selected_processo_id

        try:
            with SessionLocal() as session:
                ProducaoService(session).atualizar_processo(
                    proc_id,
                    data,
                    updated_by_id=updated_by_id,
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível guardar a produção.")
            return

        self._set_dirty(False)
        self.carregar_processos(selecionar_id=proc_id)
        self.status_label.setText("Produção guardada.")

    def _converter_orcamento(self) -> None:
        """Open the conversion dialog and create the selected production process."""
        if self._dirty:
            resposta = QMessageBox.question(
                self,
                "Alterações por gravar",
                "Há alterações por gravar. Descartar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
            self._set_dirty(False)

        dialog = ConverterOrcamentoDialog(self)
        if not dialog.exec():
            return
        if dialog.selected_orcamento_id is None or dialog.selected_versao_id is None:
            return

        created_by_id = (
            app_session.current_user.id
            if app_session.current_user is not None
            else None
        )

        try:
            with SessionLocal() as session:
                processo = converter_orcamento(
                    session,
                    orcamento_id=dialog.selected_orcamento_id,
                    versao_id=dialog.selected_versao_id,
                    created_by_id=created_by_id,
                )
                processo_id = processo.id
                codigo_processo = processo.codigo_processo
        except ValueError as error:
            QMessageBox.warning(self, "Converter Orçamento", str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível converter o orçamento.")
            return

        self.carregar_processos(selecionar_id=processo_id)
        self.status_label.setText(f"Processo {codigo_processo} criado.")

    def _on_user_edit(self, *_args) -> None:
        if self._a_preencher_form or self._selected_processo_id is None:
            return
        self._set_dirty(True)

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.save_button.setEnabled(dirty and self._selected_processo_id is not None)

    def _selecionar_processo_id(self, proc_id: int) -> bool:
        for row, processo in self._processos_by_row.items():
            if processo.id != proc_id:
                continue
            estado_sinais = self.table.blockSignals(True)
            self.table.selectRow(row)
            self.table.blockSignals(estado_sinais)
            return True
        return False

    def _processo_visivel_por_id(self, proc_id: int) -> Producao | None:
        for processo in self._processos_by_row.values():
            if processo.id == proc_id:
                return processo
        return None

    def _bloquear_sinais_form(self) -> list[tuple[QWidget, bool]]:
        widgets = [*self._readonly_widgets, *self._editable_widgets]
        return [(widget, widget.blockSignals(True)) for widget in widgets]

    @staticmethod
    def _restaurar_sinais_form(estados: list[tuple[QWidget, bool]]) -> None:
        for widget, estado_anterior in estados:
            widget.blockSignals(estado_anterior)

    @staticmethod
    def _set_combo_text(combo: QComboBox, value: object) -> None:
        text = "" if value is None else str(value).strip()
        index = combo.findText(text)
        if index >= 0:
            combo.setCurrentIndex(index)
        elif combo.isEditable():
            combo.setCurrentText(text)
        else:
            combo.setCurrentIndex(-1)

    @staticmethod
    def _none_if_empty(value: object) -> str | None:
        text = "" if value is None else str(value).strip()
        return text or None

    @staticmethod
    def _format_value(value: object) -> str:
        return "" if value is None else str(value)

    def _aplicar_larguras_colunas(self) -> None:
        for column_index, header in enumerate(self.TABLE_HEADERS):
            largura = self.COLUMN_WIDTHS.get(header)
            if largura is not None:
                self.table.setColumnWidth(column_index, largura)
