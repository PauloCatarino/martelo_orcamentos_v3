"""Production process list and detail page."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QSize, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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
    QStyle,
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
    codigo_processo_com_cliente,
    converter_orcamento,
    criar_nova_versao,
    criar_processo_externo,
    eliminar_processo_completo,
    filtrar_processos,
    gerar_nome_enc_imos_ix,
    gerar_nome_plano_cut_rite,
    listar_processos_por_encomenda,
    preparar_nova_versao,
)
from app.services.producao_pastas_service import (
    arvore_pastas_processo,
    caminho_versao_de_processo,
    preview_conteudo_pasta,
)
from app.ui import tema
from app.ui.dialogs.colunas_producao_dialog import ColunasProducaoDialog
from app.ui.dialogs.converter_orcamento_dialog import ConverterOrcamentoDialog
from app.ui.dialogs.nova_versao_processo_dialog import NovaVersaoProcessoDialog
from app.ui.dialogs.novo_processo_dialog import NovoProcessoDialog
from app.ui.dialogs.pastas_processo_dialog import PastasProcessoDialog
from app.ui.icones import icone_ficheiro
from app.ui.helpers.colunas_producao import (
    COLUNAS_PRODUCAO,
    LARGURAS_DEFAULT_PRODUCAO,
    carregar_config,
    desserializar_config,
    guardar_config,
)
from app.ui.helpers.imagem import load_scaled_pixmap
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.estado_splitter import ligar_persistencia_splitter


TIPOS_PASTA_PRODUCAO = (
    "Encomenda de Cliente",
    "Encomenda de Cliente Final",
)


class _ImagemPreviewLabel(QLabel):
    """Clickable preview label that delegates double-clicks to the page."""

    def __init__(self, on_double_click, parent=None) -> None:
        super().__init__(parent)
        self._on_double_click = on_double_click

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._on_double_click()
        super().mouseDoubleClickEvent(event)


class _DoubleClickLineEdit(QLineEdit):
    """Line edit that delegates double-clicks to the page."""

    def __init__(self, on_double_click, parent=None) -> None:
        super().__init__(parent)
        self._on_double_click = on_double_click

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._on_double_click(self)
        super().mouseDoubleClickEvent(event)


class ProducaoPage(QWidget):
    """Production process page with an editable V3 detail form."""

    TABLE_HEADERS = [coluna.titulo for coluna in COLUNAS_PRODUCAO]
    COLUMN_WIDTHS = LARGURAS_DEFAULT_PRODUCAO
    CENTERED_HEADERS = {
        "Criada em",
        "Ano",
        "Estado",
        "Nº Enc PHC",
        "V. Obra",
        "V. CutRite",
        "Data Início",
        "Data Entrega",
        "Qt Artigos",
    }

    def __init__(self) -> None:
        super().__init__()

        self._todos: list[Producao] = []
        self._processos_by_row: dict[int, Producao] = {}
        self._selected_processo_id: int | None = None
        self._dirty = False
        self._a_preencher_form = False
        self._cliente_id: int | None = None
        self._imagem_path: str | None = None
        self._imagem_preview_pixmap_original: QPixmap | None = None
        self._colunas_visiveis = [
            coluna.key for coluna in COLUNAS_PRODUCAO if coluna.visivel_default
        ]
        self._larguras_colunas = dict(LARGURAS_DEFAULT_PRODUCAO)
        self._guardar_larguras_agendado = False
        self._aplicando_config_colunas = False

        self.cabecalho = BarraCabecalho(
            "Produção",
            ["Obras em produção do Martelo V3"],
        )

        self.columns_button = QPushButton("Colunas")
        self.columns_button.setToolTip("Escolher as colunas visíveis")
        self.columns_button.clicked.connect(self._abrir_dialog_colunas)

        self.convert_button = QPushButton("Converter Orçamento")
        self.convert_button.setToolTip("Converter um orçamento adjudicado numa obra de produção")
        self.convert_button.clicked.connect(self._converter_orcamento)

        self.novo_processo_button = QPushButton("Novo Processo")
        self.novo_processo_button.setToolTip(
            "Criar uma obra a partir de uma encomenda do PHC ou do Cliente Final (Streamlit)"
        )
        self.novo_processo_button.clicked.connect(self._novo_processo)

        self.pastas_button = QPushButton("Pastas")
        self.pastas_button.setToolTip("Ver as pastas do processo selecionado no servidor")
        self.pastas_button.clicked.connect(self._abrir_pastas_processo_selecionado)

        self.open_folder_button = QPushButton("Abrir pasta")
        self.open_folder_button.setToolTip("Abrir a pasta desta obra no explorador")
        self.open_folder_button.clicked.connect(self._abrir_pasta_versao_selecionada)

        self.nova_versao_button = QPushButton("Nova Versão")
        self.nova_versao_button.setToolTip(
            "Criar nova versão de obra/CUT-RITE do processo selecionado"
        )
        self.nova_versao_button.clicked.connect(self._nova_versao)

        self.delete_button = QPushButton("Eliminar")
        self.delete_button.setToolTip("Eliminar obra: registo e/ou pasta no servidor")
        self.delete_button.clicked.connect(self._eliminar_processo)

        self.save_button = QPushButton("Salvar")
        self.save_button.setToolTip("Gravar as alterações da obra selecionada")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setToolTip("Recarregar a lista de obras")
        self.refresh_button.clicked.connect(self.carregar_processos)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.columns_button)
        actions_layout.addWidget(self.convert_button)
        actions_layout.addWidget(self.novo_processo_button)
        actions_layout.addWidget(self.pastas_button)
        actions_layout.addWidget(self.open_folder_button)
        actions_layout.addWidget(self.nova_versao_button)
        actions_layout.addWidget(self.delete_button)
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
        criada_em_item = self.table.horizontalHeaderItem(0)
        if criada_em_item is not None:
            criada_em_item.setToolTip("Data em que a obra foi criada nesta lista")
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        self._aplicar_larguras_colunas()
        header.sectionResized.connect(self._on_coluna_redimensionada)
        self._carregar_config_colunas()
        self.table.itemSelectionChanged.connect(self._on_select_row)
        self.table.cellDoubleClicked.connect(self._handle_table_double_click)

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
        self.nome_plano_corte_input = self._readonly_line()
        self.nome_plano_corte_input.setToolTip(
            "Nome do plano CUT-RITE derivado do processo"
        )
        self.nome_enc_imos_ix_input = self._readonly_line()
        self.nome_enc_imos_ix_input.setToolTip(
            "Nome da encomenda IMOS iX derivado do processo"
        )
        self.ano_input = QLineEdit()
        self.num_enc_phc_input = QLineEdit()
        self.versao_obra_input = QLineEdit()
        self.versao_obra_input.setMaxLength(2)
        self.versao_plano_input = QLineEdit()
        self.versao_plano_input.setMaxLength(2)
        self.cliente_input = self._readonly_line()
        self.cliente_simplex_input = self._readonly_line()
        self.num_cliente_phc_input = self._readonly_line()
        self.num_orcamento_input = QLineEdit()
        self.versao_orc_input = QLineEdit()
        self.preco_total_input = QLineEdit()
        self.qt_artigos_input = QLineEdit()

        self.estado_form_combo = QComboBox()
        self.estado_form_combo.addItems(ESTADOS_PRODUCAO)

        self.responsavel_form_combo = QComboBox()
        self.responsavel_form_combo.setEditable(True)

        self.ref_cliente_input = QLineEdit()
        self.obra_input = QLineEdit()
        self.localizacao_input = QLineEdit()
        self.data_inicio_input = _DoubleClickLineEdit(self._abrir_calendario_data)
        self.data_inicio_input.setPlaceholderText("dd-mm-aaaa")
        self.data_entrega_input = _DoubleClickLineEdit(self._abrir_calendario_data)
        self.data_entrega_input.setPlaceholderText("dd-mm-aaaa")

        self.tipo_pasta_combo = QComboBox()
        self.tipo_pasta_combo.addItems(TIPOS_PASTA_PRODUCAO)

        dados_grid = QGridLayout()
        dados_grid.setHorizontalSpacing(8)
        dados_grid.setVerticalSpacing(6)
        campos = [
            ("Processo", self.processo_input),
            (
                "Nome Plano CUT-RITE",
                self.nome_plano_corte_input,
                "icon_cut_rite.ico",
            ),
            (
                "Nome Enc IMOS IX",
                self.nome_enc_imos_ix_input,
                "icon_imos_2025.ico",
            ),
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
        for index, campo in enumerate(campos):
            label, widget, *icone = campo
            label_widget = (
                self._label_com_icone(label, icone[0])
                if icone
                else label
            )
            self._add_grid_field(
                dados_grid,
                index // 3,
                index % 3,
                label_widget,
                widget,
            )

        dados_widget = QWidget()
        dados_widget.setLayout(dados_grid)
        topo_layout = QHBoxLayout()
        topo_layout.setContentsMargins(0, 0, 0, 0)
        topo_layout.setSpacing(12)
        topo_layout.addWidget(dados_widget, stretch=1)
        topo_layout.addWidget(self._criar_painel_imagem(), stretch=0)

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
        layout.addLayout(topo_layout)
        layout.addLayout(textos_grid)

        self._readonly_widgets = [
            self.processo_input,
            self.nome_plano_corte_input,
            self.nome_enc_imos_ix_input,
            self.cliente_input,
            self.cliente_simplex_input,
            self.num_cliente_phc_input,
        ]
        self._editable_widgets = [
            self.ano_input,
            self.num_enc_phc_input,
            self.versao_obra_input,
            self.versao_plano_input,
            self.num_orcamento_input,
            self.versao_orc_input,
            self.preco_total_input,
            self.qt_artigos_input,
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

    def _criar_painel_imagem(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.imagem_preview = _ImagemPreviewLabel(self._abrir_imagem_pdf)
        self.imagem_preview.setText("Sem imagem")
        self.imagem_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imagem_preview.setFixedSize(280, 210)
        self.imagem_preview.setStyleSheet(
            f"QLabel {{ border: 1px solid {tema.CINZA_CASTANHO}; "
            f"background-color: {tema.BEGE_AREIA}; color: {tema.CASTANHO_ESCURO}; }}"
        )

        self.escolher_imagem_button = QPushButton("Escolher Imagem/PDF...")
        self.escolher_imagem_button.setToolTip("Escolher a imagem/PDF da obra")
        self.escolher_imagem_button.clicked.connect(self._escolher_imagem)

        self.limpar_imagem_button = QPushButton("Limpar Imagem")
        self.limpar_imagem_button.setToolTip("Remover a imagem da obra")
        self.limpar_imagem_button.clicked.connect(self._limpar_imagem)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(self.escolher_imagem_button)
        buttons_layout.addWidget(self.limpar_imagem_button)

        layout.addWidget(self.imagem_preview)
        layout.addLayout(buttons_layout)
        layout.addStretch()
        return panel

    def _label_com_icone(self, texto: str, nome_icone: str) -> QWidget:
        label_widget = QWidget()
        layout = QHBoxLayout(label_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        icon_label = QLabel()
        icon_label.setPixmap(icone_ficheiro(nome_icone).pixmap(16, 16))
        text_label = QLabel(texto)

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addStretch()
        return label_widget

    def _add_grid_field(
        self,
        grid: QGridLayout,
        row: int,
        pair_col: int,
        label: str | QWidget,
        widget: QWidget,
    ) -> None:
        col = pair_col * 2
        label_widget = label if isinstance(label, QWidget) else QLabel(label)
        grid.addWidget(label_widget, row, col)
        grid.addWidget(widget, row, col + 1)

    def _ligar_sinais_edicao(self) -> None:
        for line_edit in (
            self.ano_input,
            self.num_enc_phc_input,
            self.versao_obra_input,
            self.versao_plano_input,
            self.ref_cliente_input,
        ):
            line_edit.textChanged.connect(self._on_campo_derivado_editado)
        for line_edit in (
            self.num_cliente_phc_input,
            self.num_orcamento_input,
            self.versao_orc_input,
            self.preco_total_input,
            self.qt_artigos_input,
            self.ref_cliente_input,
            self.obra_input,
            self.localizacao_input,
            self.data_inicio_input,
            self.data_entrega_input,
        ):
            if line_edit is self.ref_cliente_input:
                continue
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
        self.ano_input.setToolTip("Ano do processo")
        self.num_enc_phc_input.setToolTip("Número da encomenda PHC")
        self.versao_obra_input.setToolTip("Versão da obra")
        self.versao_plano_input.setToolTip("Versão CUT-RITE")
        self.cliente_input.setToolTip("Cliente original do processo (fixo)")
        self.cliente_simplex_input.setToolTip(
            "Nome simplex original usado nos nomes derivados (fixo)"
        )
        self.num_cliente_phc_input.setToolTip("Número do cliente original no PHC")
        self.num_orcamento_input.setToolTip("Número do orçamento de origem")
        self.versao_orc_input.setToolTip("Versão do orçamento de origem")
        self.preco_total_input.setToolTip("Preço total da obra")
        self.qt_artigos_input.setToolTip("Quantidade de artigos")
        self.estado_form_combo.setToolTip("Estado da obra em produção")
        self.responsavel_form_combo.setToolTip("Responsável pela obra")
        self.ref_cliente_input.setToolTip("Referência do cliente")
        self.obra_input.setToolTip("Nome ou descrição curta da obra")
        self.localizacao_input.setToolTip("Localização da obra")
        self.data_inicio_input.setToolTip(
            "Data no formato dd-mm-aaaa; duplo-clique para escolher no calendário"
        )
        self.data_entrega_input.setToolTip(
            "Data no formato dd-mm-aaaa; duplo-clique para escolher no calendário"
        )
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

    def _colunas_user_id(self) -> object:
        current_user = app_session.current_user
        return getattr(current_user, "id", None) or "default"

    def _carregar_config_colunas(self) -> None:
        try:
            with SessionLocal() as session:
                visiveis, larguras = carregar_config(session, self._colunas_user_id())
        except SQLAlchemyError:
            visiveis, larguras = desserializar_config(None)

        self._colunas_visiveis = visiveis
        self._larguras_colunas = {**LARGURAS_DEFAULT_PRODUCAO, **larguras}
        self._aplicar_config_colunas()

    def _aplicar_config_colunas(self) -> None:
        visiveis = set(self._colunas_visiveis)
        self._aplicando_config_colunas = True
        try:
            for column_index, coluna in enumerate(COLUNAS_PRODUCAO):
                self.table.setColumnHidden(column_index, coluna.key not in visiveis)
                largura = self._larguras_colunas.get(
                    coluna.key,
                    LARGURAS_DEFAULT_PRODUCAO.get(coluna.key, 100),
                )
                self.table.setColumnWidth(column_index, largura)
        finally:
            self._aplicando_config_colunas = False

    def _abrir_dialog_colunas(self) -> None:
        dialog = ColunasProducaoDialog(
            self,
            COLUNAS_PRODUCAO,
            self._colunas_visiveis,
        )
        if not dialog.exec() or dialog.selected_keys is None:
            return

        self._colunas_visiveis = dialog.selected_keys
        self._aplicar_config_colunas()
        self._guardar_config_colunas()

    def _on_coluna_redimensionada(
        self,
        logical_index: int,
        _old_size: int,
        new_size: int,
    ) -> None:
        if self._aplicando_config_colunas:
            return
        if logical_index < 0 or logical_index >= len(COLUNAS_PRODUCAO):
            return

        self._larguras_colunas[COLUNAS_PRODUCAO[logical_index].key] = int(new_size)
        if self._guardar_larguras_agendado:
            return

        self._guardar_larguras_agendado = True
        QTimer.singleShot(800, self._guardar_config_colunas_debounced)

    def _guardar_config_colunas_debounced(self) -> None:
        self._guardar_larguras_agendado = False
        self._guardar_config_colunas()

    def _guardar_config_colunas(self) -> None:
        for column_index, coluna in enumerate(COLUNAS_PRODUCAO):
            self._larguras_colunas[coluna.key] = self.table.columnWidth(column_index)

        try:
            with SessionLocal() as session:
                guardar_config(
                    session,
                    self._colunas_user_id(),
                    self._colunas_visiveis,
                    self._larguras_colunas,
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel guardar as colunas.")

    def _preencher_tabela(self, processos: list[Producao]) -> None:
        """Fill the table with production processes."""
        self._processos_by_row = {}
        estado_sinais = self.table.blockSignals(True)
        self.table.setRowCount(len(processos))

        for row_index, processo in enumerate(processos):
            self._processos_by_row[row_index] = processo
            values = [coluna.valor(processo) for coluna in COLUNAS_PRODUCAO]

            for column_index, value in enumerate(values):
                coluna = COLUNAS_PRODUCAO[column_index]
                header = coluna.titulo
                display_value = self._format_value(value)
                item = self._criar_item_tabela(display_value, header)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                if coluna.key == "estado":
                    fundo, texto = tema.cor_estado_producao(value)
                    if fundo and texto:
                        item.setBackground(QColor(fundo))
                        item.setForeground(QColor(texto))
                if coluna.key == "processo":
                    item.setIcon(
                        self.style().standardIcon(
                            QStyle.StandardPixmap.SP_DirOpenIcon
                        )
                    )
                    item.setToolTip("Ver pastas do processo")
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

    def _handle_table_double_click(self, row: int, column: int) -> None:
        if column < 0 or column >= len(COLUNAS_PRODUCAO):
            return
        if COLUNAS_PRODUCAO[column].key != "processo":
            return

        processo = self._processos_by_row.get(row)
        if processo is None:
            return

        self.table.selectRow(row)
        self._abrir_pastas_processo(processo)

    def _abrir_pastas_processo_selecionado(self) -> None:
        processo = self._processo_selecionado()
        if processo is None:
            self.status_label.setText("Selecione um processo para ver as pastas.")
            return

        self._abrir_pastas_processo(processo)

    def _abrir_pastas_processo(self, processo: Producao) -> None:
        try:
            with SessionLocal() as session:
                root_path, arvore = arvore_pastas_processo(
                    session,
                    ano=processo.ano,
                    num_enc_phc=processo.num_enc_phc,
                    tipo_pasta=processo.tipo_pasta,
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as pastas do processo.")
            return

        dialog = PastasProcessoDialog(
            codigo_processo=self._format_value(processo.codigo_processo),
            root_path=root_path,
            arvore=arvore,
            parent=self,
        )
        dialog.exec()

    def _abrir_pasta_versao_selecionada(self) -> None:
        processo = self._processo_selecionado()
        if processo is None:
            self.status_label.setText("Selecione um processo para abrir a pasta.")
            return

        try:
            with SessionLocal() as session:
                processo_db = session.get(Producao, processo.id)
                if processo_db is None:
                    raise ValueError("Processo de producao nao encontrado.")
                caminho = caminho_versao_de_processo(session, processo_db)
        except (SQLAlchemyError, ValueError) as error:
            QMessageBox.warning(self, "Abrir pasta", str(error))
            return

        try:
            pasta_existe = caminho.is_dir()
        except OSError:
            pasta_existe = False
        if not pasta_existe:
            self.status_label.setText("Pasta ainda não criada.")
            QMessageBox.warning(self, "Abrir pasta", "Pasta ainda não criada.")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(caminho)))

    def _eliminar_processo(self) -> None:
        processo = self._processo_selecionado()
        if processo is None:
            self.status_label.setText("Selecione um processo para eliminar.")
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
                return
            self._set_dirty(False)

        escolha = self._escolher_modo_eliminacao(processo)
        if escolha is None:
            return
        apagar_registo, apagar_pasta = escolha

        caminho_texto = ""
        if apagar_pasta:
            try:
                with SessionLocal() as session:
                    processo_db = session.get(Producao, processo.id)
                    if processo_db is None:
                        raise ValueError("Processo de producao nao encontrado.")
                    caminho = caminho_versao_de_processo(session, processo_db)
                    caminho_texto = str(caminho)
                    preview = preview_conteudo_pasta(caminho)
            except (SQLAlchemyError, OSError, ValueError) as error:
                QMessageBox.warning(self, "Eliminar obra", str(error))
                return

            aviso_extra = ""
            if not apagar_registo:
                aviso_extra = (
                    "\n\nNota: o registo fica a apontar para uma pasta inexistente."
                )
            resposta = QMessageBox.question(
                self,
                "Confirmar eliminação da pasta",
                (
                    "A pasta abaixo será removida de forma permanente.\n\n"
                    f"{caminho_texto}\n\n"
                    "Conteúdo encontrado:\n"
                    f"{preview}"
                    f"{aviso_extra}"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return

        resposta = QMessageBox.question(
            self,
            "Confirmação final",
            self._mensagem_confirmacao_eliminacao(
                processo,
                apagar_registo=apagar_registo,
                apagar_pasta=apagar_pasta,
                caminho_pasta=caminho_texto,
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                eliminar_processo_completo(
                    session,
                    processo_id=processo.id,
                    apagar_registo=apagar_registo,
                    apagar_pasta=apagar_pasta,
                )
        except (PermissionError, OSError, ValueError) as error:
            if apagar_pasta:
                QMessageBox.warning(
                    self,
                    "Eliminar obra",
                    f"Pasta não apagada; registo mantido.\n\n{error}",
                )
            else:
                QMessageBox.warning(self, "Eliminar obra", str(error))
            return
        except SQLAlchemyError as error:
            QMessageBox.warning(
                self,
                "Eliminar obra",
                f"Não foi possível eliminar o registo na BD.\n\n{error}",
            )
            return

        selecionar_id = None if apagar_registo else processo.id
        self.carregar_processos(selecionar_id=selecionar_id)
        self.status_label.setText(
            self._mensagem_sucesso_eliminacao(
                apagar_registo=apagar_registo,
                apagar_pasta=apagar_pasta,
            )
        )

    def _escolher_modo_eliminacao(
        self,
        processo: Producao,
    ) -> tuple[bool, bool] | None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Eliminar obra")
        box.setText(
            f"Escolha o que eliminar para {self._format_value(processo.codigo_processo)}."
        )
        box.setInformativeText("Esta ação pode remover dados de forma permanente.")
        only_db_button = box.addButton(
            "Só registo (BD)",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        only_folder_button = box.addButton(
            "Só pasta (servidor)",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        both_button = box.addButton(
            "Pasta + registo",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel_button = box.addButton(
            "Cancelar",
            QMessageBox.ButtonRole.RejectRole,
        )
        box.setDefaultButton(cancel_button)
        box.setEscapeButton(cancel_button)
        box.exec()

        clicked = box.clickedButton()
        if clicked == only_db_button:
            return True, False
        if clicked == only_folder_button:
            return False, True
        if clicked == both_button:
            return True, True
        return None

    def _mensagem_confirmacao_eliminacao(
        self,
        processo: Producao,
        *,
        apagar_registo: bool,
        apagar_pasta: bool,
        caminho_pasta: str,
    ) -> str:
        codigo = self._format_value(processo.codigo_processo)
        if apagar_registo and apagar_pasta:
            return (
                f"Eliminar permanentemente a pasta e o registo da obra {codigo}?\n\n"
                f"Pasta:\n{caminho_pasta}"
            )
        if apagar_pasta:
            return (
                f"Eliminar permanentemente só a pasta da obra {codigo}?\n\n"
                f"Pasta:\n{caminho_pasta}\n\n"
                "O registo na BD será mantido."
            )
        return (
            f"Eliminar só o registo na BD da obra {codigo}?\n\n"
            "A pasta no servidor será mantida."
        )

    @staticmethod
    def _mensagem_sucesso_eliminacao(
        *,
        apagar_registo: bool,
        apagar_pasta: bool,
    ) -> str:
        if apagar_registo and apagar_pasta:
            return "Pasta e registo eliminados."
        if apagar_pasta:
            return "Pasta eliminada. O registo foi mantido."
        return "Registo eliminado. A pasta foi mantida."

    def _abrir_calendario_data(self, line_edit: QLineEdit) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Escolher data")

        calendar = QCalendarWidget(dialog)
        normalizada = normalizar_data(line_edit.text())
        if normalizada:
            qdate = QDate.fromString(normalizada, "dd-MM-yyyy")
            if qdate.isValid():
                calendar.setSelectedDate(qdate)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        calendar.activated.connect(lambda _date: dialog.accept())

        layout = QVBoxLayout(dialog)
        layout.addWidget(calendar)
        layout.addWidget(button_box)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        line_edit.setText(calendar.selectedDate().toString("dd-MM-yyyy"))

    def _nova_versao(self) -> None:
        processo = self._processo_selecionado()
        if processo is None:
            self.status_label.setText("Selecione um processo para criar nova versão.")
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
                return
            self._set_dirty(False)

        self._executar_nova_versao(processo_id=processo.id)

    def _executar_nova_versao(self, *, processo_id: int) -> None:
        try:
            with SessionLocal() as session:
                preparado = preparar_nova_versao(session, processo_id=processo_id)
        except ValueError as error:
            QMessageBox.warning(self, "Nova Versão", str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível preparar a nova versão.")
            return

        sug_cutrite = preparado["sug_cutrite"]
        sug_obra = preparado["sug_obra"]
        dialog = NovaVersaoProcessoDialog(
            versao_obra_sug_cutrite=sug_cutrite[0],
            versao_plano_sug_cutrite=sug_cutrite[1],
            versao_obra_sug_obra=sug_obra[0],
            versao_plano_sug_obra=sug_obra[1],
            existing_keys=preparado["existing_keys"],
            folder_root=preparado["folder_root"],
            folder_tree=preparado["folder_tree"],
            parent=self,
        )
        if not dialog.exec():
            return

        versao_obra, versao_plano = dialog.values()
        current_user_id = (
            app_session.current_user.id
            if app_session.current_user is not None
            else None
        )

        try:
            with SessionLocal() as session:
                novo = criar_nova_versao(
                    session,
                    processo_id=processo_id,
                    versao_obra=versao_obra,
                    versao_plano=versao_plano,
                    criar_pasta=True,
                    current_user_id=current_user_id,
                )
                novo_id = novo.id
                codigo = novo.codigo_processo
        except ValueError as error:
            QMessageBox.warning(self, "Nova Versão", str(error))
            return
        except OSError as error:
            QMessageBox.warning(self, "Nova Versão", str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível criar a nova versão.")
            return

        self.carregar_processos(selecionar_id=novo_id)
        self.status_label.setText(f"Versão {codigo} criada (+ pasta).")

    def _processo_selecionado(self) -> Producao | None:
        row = self.table.currentRow()
        processo = self._processos_by_row.get(row)
        if processo is not None:
            return processo
        if self._selected_processo_id is not None:
            return self._processo_visivel_por_id(self._selected_processo_id)
        return None

    def _fill_form(self, proc: Producao) -> None:
        """Fill detail widgets from one production process without marking dirty."""
        self._a_preencher_form = True
        estados = self._bloquear_sinais_form()
        try:
            self._cliente_id = proc.cliente_id
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
            self._imagem_path = proc.imagem_path
            self._atualizar_preview_imagem()
            self._selected_processo_id = proc.id
            self._atualizar_campos_derivados()
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
            self._cliente_id = None
            self._imagem_path = None
            self._atualizar_preview_imagem()
            self._selected_processo_id = None
        finally:
            self._restaurar_sinais_form(estados)
        self._set_dirty(False)

    def _collect_form(self) -> dict:
        """Collect editable fields from the detail form."""
        return {
            "codigo_processo": self.processo_input.text().strip(),
            "ano": self.ano_input.text().strip(),
            "num_enc_phc": self.num_enc_phc_input.text().strip(),
            "versao_obra": self.versao_obra_input.text().strip(),
            "versao_plano": self.versao_plano_input.text().strip(),
            "cliente_id": self._cliente_id,
            "nome_cliente": self._none_if_empty(self.cliente_input.text()),
            "nome_cliente_simplex": self._none_if_empty(
                self.cliente_simplex_input.text()
            ),
            "num_cliente_phc": self._none_if_empty(self.num_cliente_phc_input.text()),
            "num_orcamento": self._none_if_empty(self.num_orcamento_input.text()),
            "versao_orc": self._none_if_empty(self.versao_orc_input.text()),
            "preco_total": self._decimal_or_none(self.preco_total_input.text()),
            "qt_artigos": self._int_or_none(self.qt_artigos_input.text()),
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
            "imagem_path": self._imagem_path,
        }

    def _validar_obrigatorios_para_gravar(self, data: dict) -> bool:
        obrigatorios = (
            ("ano", "Ano"),
            ("num_enc_phc", "Nº Enc PHC"),
            ("versao_obra", "V. Obra"),
            ("versao_plano", "V. CutRite"),
        )
        for campo, label in obrigatorios:
            if not str(data.get(campo) or "").strip():
                QMessageBox.warning(self, "Guardar produção", f"Preencha {label}.")
                return False

        if not data.get("data_inicio"):
            QMessageBox.warning(
                self,
                "Guardar produção",
                "Preencha a Data Início no formato dd-mm-aaaa.",
            )
            return False
        if not data.get("data_entrega"):
            QMessageBox.warning(
                self,
                "Guardar produção",
                "Preencha a Data Entrega no formato dd-mm-aaaa.",
            )
            return False
        return True

    def _save(self) -> None:
        """Persist the selected production process edits."""
        if self._selected_processo_id is None:
            self.status_label.setText("Selecione uma obra de produção.")
            return

        try:
            data = self._collect_form()
        except ValueError as error:
            QMessageBox.warning(self, "Guardar produção", str(error))
            return
        if not self._validar_obrigatorios_para_gravar(data):
            return
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
        except ValueError as error:
            QMessageBox.warning(self, "Guardar produção", str(error))
            return
        except SQLAlchemyError:
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

    def _novo_processo(self) -> None:
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

        dialog = NovoProcessoDialog(self)
        if not dialog.exec():
            return
        dados = dialog.result_data()
        if not dados:
            return

        try:
            with SessionLocal() as session:
                existentes = listar_processos_por_encomenda(
                    session,
                    ano=dados.get("ano"),
                    num_enc_phc=dados.get("num_enc_phc"),
                )
                existentes_info = [
                    {
                        "id": p.id,
                        "codigo": p.codigo_processo,
                        "estado": p.estado,
                        "versao_obra": p.versao_obra,
                        "versao_plano": p.versao_plano,
                        "data_inicio": p.data_inicio,
                        "data_entrega": p.data_entrega,
                    }
                    for p in existentes
                ]
        except SQLAlchemyError:
            existentes_info = []

        if existentes_info:
            self._tratar_encomenda_existente(dados, existentes_info)
            return

        current_user = app_session.current_user
        created_by_id = current_user.id if current_user is not None else None
        partes_nome = (current_user.nome or "").split() if current_user is not None else []
        responsavel = partes_nome[0] if partes_nome else None
        try:
            with SessionLocal() as session:
                processo = criar_processo_externo(
                    session,
                    dados=dados,
                    responsavel=responsavel,
                    created_by_id=created_by_id,
                )
                processo_id = processo.id
                codigo_processo = processo.codigo_processo
                pasta_servidor = processo.pasta_servidor or ""
        except ValueError as error:
            QMessageBox.warning(self, "Novo Processo", str(error))
            return
        except OSError as error:
            QMessageBox.warning(
                self,
                "Novo Processo",
                f"Processo não criado (falha ao criar a pasta no servidor):\n\n{error}",
            )
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível criar o processo.")
            return

        self.carregar_processos(selecionar_id=processo_id)
        mensagem = f"Processo {codigo_processo} criado."
        if pasta_servidor:
            mensagem += f"\n\nPasta criada no servidor:\n{pasta_servidor}"
        QMessageBox.information(self, "Novo Processo", mensagem)
        self.status_label.setText(f"Processo {codigo_processo} criado.")

    def _tratar_encomenda_existente(self, dados: dict, existentes: list[dict]) -> None:
        linhas = "\n".join(
            f"  • {e['codigo']} — {e['estado'] or 'sem estado'}"
            f" (Início {e['data_inicio'] or '—'}, Entrega {e['data_entrega'] or '—'})"
            for e in existentes
        )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Encomenda já existe")
        box.setText(
            f"Já existe obra para esta encomenda "
            f"(Ano {dados.get('ano')}, Nº Enc {dados.get('num_enc_phc')})."
        )
        box.setInformativeText(
            f"{linhas}\n\nQuer criar uma NOVA VERSÃO (da Obra ou de CUT-RITE) "
            "a partir da existente?"
        )
        nova_versao_btn = box.addButton("Nova Versão", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not nova_versao_btn:
            return

        base = max(
            existentes,
            key=lambda e: (str(e["versao_obra"] or ""), str(e["versao_plano"] or "")),
        )
        self._executar_nova_versao(processo_id=base["id"])

    def _on_user_edit(self, *_args) -> None:
        if self._a_preencher_form or self._selected_processo_id is None:
            return
        self._set_dirty(True)

    def _on_campo_derivado_editado(self, *_args) -> None:
        self._atualizar_campos_derivados()
        self._on_user_edit()

    def _atualizar_campos_derivados(self) -> None:
        ano = self.ano_input.text()
        num_enc_phc = self.num_enc_phc_input.text()
        versao_obra = self.versao_obra_input.text()
        versao_plano = self.versao_plano_input.text()
        nome_cliente = self.cliente_input.text()
        nome_simplex = self.cliente_simplex_input.text()
        ref_cliente = self.ref_cliente_input.text()

        self.processo_input.setText(
            codigo_processo_com_cliente(
                ano,
                num_enc_phc,
                versao_obra,
                versao_plano,
                nome_simplex=nome_simplex,
                nome_cliente=nome_cliente,
                ref_cliente=ref_cliente,
            )
        )
        self.nome_plano_corte_input.setText(
            gerar_nome_plano_cut_rite(
                ano,
                num_enc_phc,
                versao_obra,
                versao_plano,
                nome_cliente_simplex=nome_simplex,
                nome_cliente=nome_cliente,
                ref_cliente=ref_cliente,
            )
        )
        self.nome_enc_imos_ix_input.setText(
            gerar_nome_enc_imos_ix(
                ano,
                num_enc_phc,
                versao_obra,
                nome_cliente_simplex=nome_simplex,
                nome_cliente=nome_cliente,
                ref_cliente=ref_cliente,
            )
        )

    def _escolher_imagem(self) -> None:
        caminho, _filtro = QFileDialog.getOpenFileName(
            self,
            "Escolher Imagem/PDF da obra",
            "",
            "Imagens e PDF (*.png *.jpg *.jpeg *.bmp *.pdf);;Todos (*)",
        )
        if not caminho:
            return

        self._imagem_path = caminho
        self._atualizar_preview_imagem()
        self._set_dirty(True)

    def _limpar_imagem(self) -> None:
        self._imagem_path = None
        self._atualizar_preview_imagem()
        self._set_dirty(True)

    def _atualizar_preview_imagem(self) -> None:
        if not hasattr(self, "imagem_preview"):
            return

        caminho = self._imagem_path
        self._imagem_preview_pixmap_original = None
        self.imagem_preview.setPixmap(QPixmap())
        self.imagem_preview.setToolTip(caminho or "")

        if not caminho:
            self.imagem_preview.setText("Sem imagem")
            return

        path = Path(caminho)
        if not path.is_file():
            self.imagem_preview.setText("Imagem não encontrada")
            return

        if path.suffix.lower() == ".pdf":
            self._imagem_preview_pixmap_original = self._carregar_pdf_pixmap(path)
            if self._imagem_preview_pixmap_original is None:
                self.imagem_preview.setText("PDF — duplo-clique para abrir")
                return
            self._ajustar_imagem_preview()
            return

        self._imagem_preview_pixmap_original = QPixmap(str(path))
        if self._imagem_preview_pixmap_original is None:
            self.imagem_preview.setText("Imagem não encontrada")
            return
        if self._imagem_preview_pixmap_original.isNull():
            self._imagem_preview_pixmap_original = load_scaled_pixmap(
                str(path),
                self.imagem_preview.size(),
            )
        if self._imagem_preview_pixmap_original is None:
            self.imagem_preview.setText("Imagem não encontrada")
            return
        self._ajustar_imagem_preview()

    def _ajustar_imagem_preview(self) -> None:
        if not hasattr(self, "imagem_preview"):
            return
        original = self._imagem_preview_pixmap_original
        if original is None or original.isNull():
            return

        tamanho = self.imagem_preview.size()
        scaled = original.scaled(
            max(tamanho.width() - 4, 1),
            max(tamanho.height() - 4, 1),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.imagem_preview.setText("")
        self.imagem_preview.setPixmap(scaled)

    def _carregar_pdf_pixmap(self, caminho: Path) -> QPixmap | None:
        try:
            from PySide6.QtPdf import QPdfDocument
        except (ImportError, ModuleNotFoundError):
            return None

        try:
            document = QPdfDocument(self)
            document.load(str(caminho))
            if document.pageCount() < 1:
                return None
            image = document.render(0, QSize(900, 1200))
            if image.isNull():
                return None
            return QPixmap.fromImage(image)
        except Exception:
            return None

    def _abrir_imagem_pdf(self) -> None:
        if not self._imagem_path:
            return
        path = Path(self._imagem_path)
        if not path.is_file():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

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
    def _decimal_or_none(value: object) -> Decimal | None:
        text = "" if value is None else str(value).strip()
        if not text:
            return None
        text = text.replace(" ", "").replace(",", ".")
        try:
            return Decimal(text)
        except InvalidOperation as exc:
            raise ValueError("Preço total inválido.") from exc

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        text = "" if value is None else str(value).strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError("Qt artigos inválida.") from exc

    @staticmethod
    def _format_value(value: object) -> str:
        return "" if value is None else str(value)

    @staticmethod
    def _format_date(value: object) -> str:
        if value is None:
            return ""
        try:
            return value.strftime("%d-%m-%Y")
        except AttributeError:
            return ""

    def _aplicar_larguras_colunas(self) -> None:
        for column_index, coluna in enumerate(COLUNAS_PRODUCAO):
            largura = self.COLUMN_WIDTHS.get(coluna.key)
            if largura is not None:
                self.table.setColumnWidth(column_index, largura)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._ajustar_imagem_preview()
