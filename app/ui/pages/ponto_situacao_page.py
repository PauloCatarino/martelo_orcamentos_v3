"""Page "Ponto Situacao": production dashboard."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QHorizontalBarSeries,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPageLayout, QPageSize, QPainter, QPdfWriter
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.producao_estados import ESTADOS_PRODUCAO
from app.services.estado_producao_service import estado_producao_por_processo
from app.services.producao_dashboard_service import calcular_dashboard
from app.services.producao_phc_sync_service import (
    aplicar_estados,
    detetar_diferencas_estado_phc,
    detetar_diferencas_estado_streamlit,
)
from app.services.producao_precos_service import (
    aplicar_precos,
    detetar_diferencas_preco,
)
from app.services.producao_service import ProducaoService, filtrar_processos
from app.ui import tema
from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog
from app.ui.dialogs.producao_precos_dialog import ProducaoPrecosDialog
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras

CORES_ESTADO = {
    "Desenho": "#2A78D6",
    "Producao": "#EDA100",
    "Finalizado": "#1BAF7A",
    "Arquivado": "#888780",
}

# Setores do Estado de Produ\u00e7\u00e3o, pela mesma ordem do dom\u00ednio PD1.
SETORES_ORDEM = (
    "Stock",
    "Prepara\u00e7\u00e3o",
    "Corte",
    "Orlagem",
    "CNC",
    "Montagem",
    "Embalagem",
    "Expedi\u00e7\u00e3o",
)

# Cores das c\u00e9lulas de setor: conclu\u00eddo (verde), parcial (\u00e2mbar); cinza vem do tema.
COR_SETOR_OK = "#1BAF7A"
COR_SETOR_PARCIAL = "#EDA100"


class _ClickableFrame(QFrame):
    def __init__(self, on_click) -> None:
        super().__init__()
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_click()
        super().mousePressEvent(event)


class PontoSituacaoPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._kpis: dict[str, QLabel] = {}
        # Lazy load do separador "Estado de Produ\u00e7\u00e3o" (query Streamlit de rede).
        self._estado_carregado = False

        self.cabecalho = BarraCabecalho(
            "Ponto Situa\u00e7\u00e3o",
            ["Estado das obras em produ\u00e7\u00e3o"],
        )

        self.campo_pesquisa = CampoPesquisa()
        self.campo_pesquisa.setToolTip(
            "O Resumo atualiza ao vivo; prima Enter para pesquisar o Estado de "
            "Produção (evita consultas ao Streamlit a cada tecla)."
        )
        # "Resumo" (local, rápido) atualiza a cada tecla; o "Estado de Produção"
        # (query Streamlit, lenta) só refaz a consulta ao premir Enter.
        self.campo_pesquisa.pesquisa_mudou.connect(self._carregar)
        self.campo_pesquisa.pesquisar.connect(self._pos_filtros)
        self.campo_pesquisa.limpar_clicado.connect(self._limpar_filtros)

        self.utilizador_combo = QComboBox()
        self.cliente_combo = QComboBox()
        self.estado_combo = QComboBox()
        for combo in (self.utilizador_combo, self.cliente_combo, self.estado_combo):
            combo.currentTextChanged.connect(self._ao_mudar_filtros)

        self.atualizar_button = QPushButton("Atualizar")
        self.atualizar_button.setToolTip("Recalcular o dashboard")
        self.atualizar_button.clicked.connect(self._carregar)

        self.exportar_pdf_button = QPushButton("Exportar PDF")
        self.exportar_pdf_button.setToolTip(
            "Exportar o dashboard atual, com os filtros aplicados, para PDF"
        )
        self.exportar_pdf_button.clicked.connect(self._exportar_pdf)

        self.sincronizar_phc_button = QPushButton("Sincronizar PHC")
        self.sincronizar_phc_button.setToolTip(
            "Comparar e atualizar os estados das obras a partir do PHC"
        )
        self.sincronizar_phc_button.clicked.connect(self._sincronizar_phc)

        self.validar_precos_button = QPushButton("Validar pre\u00e7os")
        self.validar_precos_button.setToolTip(
            "Comparar e atualizar os pre\u00e7os de venda a partir do PHC/Streamlit"
        )
        self.validar_precos_button.clicked.connect(self._validar_precos)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        toolbar.addWidget(self.campo_pesquisa)
        toolbar.addWidget(QLabel("Estado"))
        toolbar.addWidget(self.estado_combo)
        toolbar.addWidget(QLabel("Cliente"))
        toolbar.addWidget(self.cliente_combo)
        toolbar.addWidget(QLabel("Utilizador"))
        toolbar.addWidget(self.utilizador_combo)
        toolbar.addWidget(self.atualizar_button)
        toolbar.addWidget(self.exportar_pdf_button)
        toolbar.addWidget(self.sincronizar_phc_button)
        toolbar.addWidget(self.validar_precos_button)
        toolbar.addStretch()

        self.atualizado_label = QLabel("")
        self.atualizado_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        for chave, titulo, cor, tooltip in (
            ("total", "Total obras", None,
             "N\u00ba total de obras (com os filtros aplicados)."),
            ("desenho", "Em desenho", None, "Obras no estado Desenho."),
            ("producao", "Em produ\u00e7\u00e3o", None, "Obras no estado Producao."),
            ("finalizadas", "Finalizadas", None, "Obras no estado Finalizado."),
            ("arquivadas", "Arquivadas", None, "Obras no estado Arquivado."),
            ("atrasadas", "Atrasadas", "#A32D2D",
             "Obras em aberto (n\u00e3o Finalizadas/Arquivadas) com entrega j\u00e1 passada."),
            ("valor_total", "Valor total", None,
             "Soma do pre\u00e7o de TODAS as obras (inclui Finalizadas/Arquivadas)."),
            ("valor", "Valor em aberto", None,
             "Soma do pre\u00e7o das obras ainda EM ABERTO (n\u00e3o Finalizadas/Arquivadas)."),
            ("sem_preco", "Sem pre\u00e7o", "#854F0B",
             "Obras em aberto sem pre\u00e7o atribu\u00eddo (pre\u00e7o por preencher)."),
        ):
            on_click = self._ir_para_atrasadas if chave == "atrasadas" else None
            card, valor = self._criar_kpi(titulo, cor, on_click, tooltip)
            self._kpis[chave] = valor
            kpi_row.addWidget(card)

        self.estado_box = QVBoxLayout()
        self.responsavel_box = QVBoxLayout()
        self.clientes_box = QVBoxLayout()

        w_estado = QWidget()
        w_estado.setLayout(self.estado_box)
        w_estado.setMinimumHeight(300)
        w_resp = QWidget()
        w_resp.setLayout(self.responsavel_box)
        w_resp.setMinimumHeight(300)
        w_cli = QWidget()
        w_cli.setLayout(self.clientes_box)
        w_cli.setMinimumHeight(360)

        topo_graf = QHBoxLayout()
        topo_graf.addWidget(w_estado, stretch=1)
        topo_graf.addWidget(w_resp, stretch=1)

        self.atrasadas_table = self._criar_tabela_atrasadas()
        self.atrasadas_group = QGroupBox("Obras atrasadas")
        self.atrasadas_group.setStyleSheet(
            f"QGroupBox {{ color: {tema.CASTANHO_ESCURO}; font-weight: bold; }}"
        )
        atrasadas_layout = QVBoxLayout(self.atrasadas_group)
        atrasadas_layout.setContentsMargins(8, 12, 8, 8)
        atrasadas_layout.addWidget(self.atrasadas_table)

        self.report_widget = QWidget()
        report_layout = QVBoxLayout(self.report_widget)
        report_layout.setContentsMargins(0, 0, 0, 0)
        report_layout.setSpacing(12)
        report_layout.addLayout(kpi_row)
        report_layout.addLayout(topo_graf)
        report_layout.addWidget(w_cli)
        report_layout.addWidget(self.atrasadas_group)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidget(self.report_widget)

        # Separador "Estado de Produção" (chão de fábrica), com carregamento lazy.
        self.estado_widget = self._criar_aba_estado()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.scroll, "Resumo")
        self.tabs.addTab(self.estado_widget, "Estado de Produção")
        self.tabs.currentChanged.connect(self._ao_mudar_tab)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(toolbar)
        # Linha de acompanhamento logo abaixo da toolbar, sempre visível em
        # ambos os separadores (como nos outros menus).
        layout.addWidget(self.atualizado_label)
        layout.addWidget(self.tabs, stretch=1)

        self._carregar()

    def _criar_kpi(self, titulo, cor=None, on_click=None, tooltip=None):
        card = _ClickableFrame(on_click) if on_click is not None else QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {tema.BEGE_AREIA}; border-radius: 8px; }}"
        )
        if tooltip:
            card.setToolTip(tooltip)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        titulo_label = QLabel(titulo)
        titulo_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO}; font-size: 12px;")

        valor_label = QLabel("-")
        valor_label.setStyleSheet(
            f"color: {cor or tema.CASTANHO_ESCURO}; "
            "font-size: 22px; font-weight: bold;"
        )
        if on_click is not None:
            titulo_label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            valor_label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )

        lay.addWidget(titulo_label)
        lay.addWidget(valor_label)
        return card, valor_label

    def _criar_tabela_atrasadas(self) -> QTableWidget:
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(
            [
                "Processo",
                "Cliente",
                "Respons\u00e1vel",
                "Data Entrega",
                "Dias Atraso",
            ]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setFixedHeight(260)

        header = table.horizontalHeader()
        # Colunas redimensionáveis (e persistentes por máquina) -> modo Interactive.
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        for indice, largura in enumerate((180, 420, 110, 110, 90)):
            table.setColumnWidth(indice, largura)
        ligar_persistencia_larguras(table, "ponto_situacao_atrasadas")
        return table

    # ----- Separador "Estado de Produção" (PD3) -----

    def _criar_aba_estado(self) -> QWidget:
        self.estado_info_label = QLabel(
            "Carregue 'Atualizar estado' para consultar o estado no Streamlit."
        )
        self.estado_info_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        self.atualizar_estado_button = QPushButton("Atualizar estado")
        self.atualizar_estado_button.setToolTip(
            "Reconsultar o estado de produção no Streamlit"
        )
        self.atualizar_estado_button.clicked.connect(self._carregar_estado)

        topo = QHBoxLayout()
        topo.addWidget(self.estado_info_label, stretch=1)
        topo.addWidget(self.atualizar_estado_button)

        self.estado_table = self._criar_tabela_estado()

        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addLayout(topo)
        lay.addWidget(self.estado_table, stretch=1)
        return widget

    def _criar_tabela_estado(self) -> QTableWidget:
        colunas = [
            "Processo",
            "Cliente",
            "Enc PHC",
            "Enc Streamlit",
            "Ref Cliente",
            "Responsável",
            "Estado",
            "Preço",
            "% Global",
            *SETORES_ORDEM,
        ]
        # Índices dinâmicos (sem números mágicos): preço a seguir a "Estado", a barra
        # na coluna "% Global" e os setores logo a seguir.
        self._estado_idx_preco = colunas.index("Preço")
        self._estado_idx_global = colunas.index("% Global")
        self._estado_idx_setor0 = self._estado_idx_global + 1

        table = QTableWidget(0, len(colunas))
        table.setHorizontalHeaderLabels(colunas)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)

        header = table.horizontalHeader()
        # Todas as colunas redimensionáveis (e persistentes) -> modo Interactive.
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )

        # Larguras-base sensatas (os setores ficam todos com o mesmo default).
        larguras_base = {
            "Processo": 170,
            "Cliente": 260,
            "Enc PHC": 80,
            "Enc Streamlit": 100,
            "Ref Cliente": 110,
            "Responsável": 90,
            "Estado": 90,
            "Preço": 100,
            "% Global": 140,
        }
        for indice, nome in enumerate(colunas):
            table.setColumnWidth(indice, larguras_base.get(nome, 80))

        # Restaura larguras guardadas (por máquina) por cima das base e persiste
        # ao arrastar; só atua em colunas Interactive (acima).
        ligar_persistencia_larguras(table, "ponto_situacao_estado")
        return table

    def _ao_mudar_tab(self, index) -> None:
        """Alterna os botões do Resumo e faz o lazy load do separador Estado."""
        # Os 4 botões só fazem sentido no "Resumo"; esconde-os no separador Estado.
        em_resumo = self.tabs.widget(index) is self.scroll
        for botao in (
            self.atualizar_button,
            self.exportar_pdf_button,
            self.sincronizar_phc_button,
            self.validar_precos_button,
        ):
            botao.setVisible(em_resumo)
        if not em_resumo and not self._estado_carregado:
            self._carregar_estado()

    def _ao_mudar_filtros(self, *_args) -> None:
        """Filtros mudaram: recarrega o dashboard e trata do separador Estado."""
        self._carregar()
        self._pos_filtros()

    def _pos_filtros(self) -> None:
        # Se o separador ativo for o de Estado, recarrega; senão invalida para
        # recarregar só na próxima abertura (evita queries Streamlit no "Resumo").
        if self.tabs.currentWidget() is self.estado_widget:
            self._carregar_estado()
        else:
            self._estado_carregado = False

    def _carregar_estado(self, *_args) -> None:
        texto = self.campo_pesquisa.texto()
        utilizador = self._combo_valor(self.utilizador_combo)
        cliente = self._combo_valor(self.cliente_combo)
        estado = self._combo_valor(self.estado_combo)

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.estado_info_label.setText("A consultar o estado no Streamlit...")
        QApplication.processEvents()
        try:
            with SessionLocal() as session:
                todos = ProducaoService(session).listar_processos()
                filtrados = filtrar_processos(
                    todos,
                    texto=texto,
                    estado=estado,
                    cliente=cliente,
                    responsavel=utilizador,
                )
                resultados = estado_producao_por_processo(
                    session, processos=filtrados
                )
        except Exception as exc:  # ligacao/SQL/config Streamlit
            self.estado_info_label.setText(
                "Não foi possível consultar o estado de produção."
            )
            QMessageBox.warning(
                self,
                "Estado de Produção",
                self._mensagem_erro_fonte(exc, "Streamlit"),
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        self._preencher_estado(resultados)
        self._estado_carregado = True
        self.estado_info_label.setText(self._texto_estado(resultados))

    def _preencher_estado(self, resultados) -> None:
        table = self.estado_table
        idx_global = self._estado_idx_global
        idx_setor0 = self._estado_idx_setor0
        table.setRowCount(len(resultados))
        for row, obra in enumerate(resultados):
            # Células de texto, na mesma ordem das colunas até "% Global".
            textos = (
                obra.codigo,
                obra.cliente,
                obra.enc_phc,
                obra.enc_streamlit,
                obra.ref_cliente,
                obra.responsavel,
                obra.estado_local,
            )
            for coluna, valor in enumerate(textos):
                item = QTableWidgetItem(valor or "")
                if valor:
                    item.setToolTip(valor)
                if obra.concluido_sem_preco:
                    item.setToolTip(
                        (item.toolTip() + "\n" if item.toolTip() else "")
                        + "⚠️ Concluído sem preço"
                    )
                table.setItem(row, coluna, item)

            # "Preço" (preço externo na fonte certa) entre "Estado" e "% Global".
            table.setItem(row, self._estado_idx_preco, self._item_preco(obra))

            table.setCellWidget(row, idx_global, self._barra_global(obra))

            medias = {s.nome: s.media_pct for s in obra.estado.setores}
            for indice, nome in enumerate(SETORES_ORDEM):
                table.setItem(row, idx_setor0 + indice, self._item_setor(nome, medias))

    def _barra_global(self, obra) -> QProgressBar:
        barra = QProgressBar()
        barra.setRange(0, 100)
        barra.setValue(int(round(obra.estado.global_pct)))
        barra.setFormat(obra.estado.etiqueta)
        barra.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cor = CORES_ESTADO.get(obra.estado_local, tema.CINZA_CASTANHO)
        barra.setStyleSheet(
            "QProgressBar {{ border: 1px solid {borda}; border-radius: 4px; "
            "background: {fundo}; text-align: center; color: {texto}; }} "
            "QProgressBar::chunk {{ background-color: {cor}; border-radius: 3px; }}".format(
                borda=tema.CINZA_CASTANHO,
                fundo=tema.BEGE_AREIA,
                texto=tema.CASTANHO_ESCURO,
                cor=cor,
            )
        )
        tooltip = obra.estado.etiqueta
        if obra.concluido_sem_preco:
            tooltip += "  ⚠️ sem preço"
        barra.setToolTip(tooltip)
        return barra

    def _item_setor(self, nome, medias) -> QTableWidgetItem:
        if nome not in medias:
            item = QTableWidgetItem("—")  # em dash
            item.setForeground(QColor(tema.CINZA_CASTANHO))
            item.setToolTip(f"{nome}: não aplicável nesta obra")
        else:
            media = medias[nome]
            if media >= 100:
                texto, cor = "100%", COR_SETOR_OK
            elif media > 0:
                texto, cor = f"{media:.0f}%", COR_SETOR_PARCIAL
            else:
                texto, cor = "0%", tema.CINZA_CASTANHO
            item = QTableWidgetItem(texto)
            item.setForeground(QColor(cor))
            item.setToolTip(f"{nome}: {media:.1f}%")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _item_preco(self, obra) -> QTableWidgetItem:
        preco = obra.preco_externo
        if preco is None:
            item = QTableWidgetItem("—")  # em dash
            item.setForeground(QColor(tema.CINZA_CASTANHO))
            item.setToolTip(f"Sem preço na fonte ({obra.fonte_preco or 's/ fonte'})")
        else:
            texto = self._fmt_euro(preco)
            item = QTableWidgetItem(texto)
            item.setToolTip(f"Preço {obra.fonte_preco}: {texto}")
            if preco <= 0:
                item.setForeground(QColor(COR_SETOR_PARCIAL))
        if obra.concluido_sem_preco:
            item.setForeground(QColor("#A32D2D"))
            item.setToolTip(item.toolTip() + "\n⚠️ Concluído sem preço")
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        return item

    @staticmethod
    def _fmt_euro(valor) -> str:
        # Formato pt-PT: milhares com ".", decimais com "," (ex.: "1.234,56 €").
        texto = f"{float(valor):,.2f}"
        texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{texto} €"

    def _texto_estado(self, resultados) -> str:
        encontrados = sum(1 for obra in resultados if obra.encontrado)
        sem_preco = sum(1 for obra in resultados if obra.concluido_sem_preco)
        hoje = datetime.now().strftime("%d-%m-%Y")
        texto = (
            f"{len(resultados)} obras ({encontrados} com dados no Streamlit) "
            f"· atualizado {hoje}"
        )
        if sem_preco:
            texto += f" · {sem_preco} sem preço"
        return texto

    def _ir_para_atrasadas(self) -> None:
        self.scroll.ensureWidgetVisible(self.atrasadas_group)

    def _carregar(self, *_args) -> None:
        texto = self.campo_pesquisa.texto()
        utilizador = self._combo_valor(self.utilizador_combo)
        cliente = self._combo_valor(self.cliente_combo)
        estado = self._combo_valor(self.estado_combo)

        try:
            with SessionLocal() as session:
                dados = calcular_dashboard(
                    session,
                    texto=texto,
                    utilizador=utilizador,
                    cliente=cliente,
                    estado=estado,
                )
                opcoes = (
                    dados
                    if not any((texto, utilizador, cliente, estado))
                    else calcular_dashboard(session)
                )
        except SQLAlchemyError:
            self.atualizado_label.setText(
                "N\u00e3o foi poss\u00edvel carregar o dashboard."
            )
            return

        self._atualizar_combos(opcoes)

        self._kpis["total"].setText(str(dados.total))
        self._kpis["desenho"].setText(str(dados.em_desenho))
        self._kpis["producao"].setText(str(dados.em_producao))
        self._kpis["finalizadas"].setText(str(dados.finalizadas))
        self._kpis["arquivadas"].setText(str(dados.arquivadas))
        self._kpis["atrasadas"].setText(str(dados.atrasadas))
        self._kpis["valor_total"].setText(
            f"{dados.valor_total:,.0f} \u20ac".replace(",", ".")
        )
        self._kpis["valor"].setText(
            f"{dados.valor_aberto:,.0f} \u20ac".replace(",", ".")
        )
        self._kpis["sem_preco"].setText(str(dados.sem_preco))

        self._substituir(self.estado_box, self._grafico_estado(dados))
        self._substituir(self.responsavel_box, self._grafico_responsavel(dados))
        self._substituir(self.clientes_box, self._grafico_clientes(dados))
        self._preencher_atrasadas(dados)
        self.atualizado_label.setText(self._texto_atualizado(dados))

    def _preencher_atrasadas(self, dados) -> None:
        lista = dados.lista_atrasadas
        self.atrasadas_table.setRowCount(len(lista))
        for row_index, row in enumerate(lista):
            valores = (
                row["codigo"],
                row["cliente"],
                row["responsavel"],
                row["data_entrega"],
                str(row["dias_atraso"]),
            )
            for column_index, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                if valor:
                    item.setToolTip(valor)
                if column_index == 4:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.atrasadas_table.setItem(row_index, column_index, item)
        self.atrasadas_group.setTitle(f"Obras atrasadas ({len(lista)})")

    def _exportar_pdf(self) -> None:
        caminho, _filtro = QFileDialog.getSaveFileName(
            self,
            "Exportar dashboard (PDF)",
            "Ponto_Situacao.pdf",
            "PDF (*.pdf)",
        )
        if not caminho:
            return
        if not caminho.lower().endswith(".pdf"):
            caminho += ".pdf"

        pixmap = self.report_widget.grab()
        writer = QPdfWriter(caminho)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageOrientation(QPageLayout.Orientation.Landscape)
        writer.setResolution(150)

        painter = QPainter(writer)
        try:
            area = painter.viewport()
            escala = pixmap.scaled(
                area.width(),
                area.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (area.width() - escala.width()) // 2
            painter.drawPixmap(x, 0, escala)
        finally:
            painter.end()

        self.atualizado_label.setText(f"PDF exportado: {caminho}")

    def _sincronizar_phc(self) -> None:
        current_user = app_session.current_user
        nome_login = (
            current_user.nome.split()[0]
            if current_user is not None and current_user.nome
            else ""
        )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Sincronizar PHC")
        box.setText("Atualizar os estados de que obras?")
        btn_minhas = box.addButton(
            f"S\u00f3 as minhas ({nome_login})" if nome_login else "S\u00f3 as minhas",
            QMessageBox.ButtonRole.AcceptRole,
        )
        btn_todas = box.addButton(
            "Todos os utilizadores",
            QMessageBox.ButtonRole.AcceptRole,
        )
        box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(btn_minhas)
        box.exec()
        clicado = box.clickedButton()
        if clicado is None or clicado not in (btn_minhas, btn_todas):
            return
        responsavel = nome_login if clicado is btn_minhas else None

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.atualizado_label.setText("A consultar o PHC/Streamlit...")
        QApplication.processEvents()
        try:
            try:
                with SessionLocal() as session:
                    diffs_phc = detetar_diferencas_estado_phc(
                        session,
                        responsavel=responsavel,
                    )
            except Exception as exc:  # ligacao/SQL/config PHC
                diffs_phc = []
                erro_phc = exc
            else:
                erro_phc = None

            try:
                with SessionLocal() as session:
                    diffs_streamlit = detetar_diferencas_estado_streamlit(
                        session,
                        responsavel=responsavel,
                    )
            except Exception as exc:  # ligacao/SQL/config Streamlit
                diffs_streamlit = []
                erro_streamlit = exc
            else:
                erro_streamlit = None

            diffs = diffs_phc + diffs_streamlit
            diffs.sort(key=lambda d: d["codigo"].casefold())
        finally:
            QApplication.restoreOverrideCursor()

        if erro_phc is not None and erro_streamlit is not None:
            QMessageBox.warning(
                self,
                "Sincronizar PHC",
                self._mensagem_erro_phc(erro_phc),
            )
            return

        avisos = []
        if erro_phc is not None:
            avisos.append(self._mensagem_erro_fonte(erro_phc, "PHC"))
        if erro_streamlit is not None:
            avisos.append(self._mensagem_erro_fonte(erro_streamlit, "Streamlit"))
        if avisos:
            QMessageBox.information(
                self,
                "Sincronizar PHC",
                "A sincronização vai continuar só com a fonte disponível:\n\n"
                + "\n\n".join(avisos),
            )

        if not diffs:
            QMessageBox.information(
                self,
                "Sincronizar PHC",
                "Estados j\u00e1 sincronizados - sem diferen\u00e7as face ao PHC/Streamlit.",
            )
            self._carregar()
            return

        dialog = ProducaoPhcSyncDialog(diffs, self)
        if not dialog.exec():
            return

        atualizacoes = dialog.selecionados()
        if not atualizacoes:
            return

        current_user_id = (
            app_session.current_user.id
            if app_session.current_user is not None
            else None
        )
        try:
            with SessionLocal() as session:
                n = aplicar_estados(
                    session,
                    atualizacoes,
                    current_user_id=current_user_id,
                )
        except SQLAlchemyError:
            QMessageBox.warning(
                self,
                "Sincronizar PHC",
                "N\u00e3o foi poss\u00edvel atualizar os estados.",
            )
            return

        self._carregar()
        QMessageBox.information(
            self,
            "Sincronizar PHC",
            f"{n} obra(s) atualizada(s) a partir do PHC/Streamlit.",
        )

    def _validar_precos(self) -> None:
        current_user = app_session.current_user
        nome_login = (
            current_user.nome.split()[0]
            if current_user is not None and current_user.nome
            else ""
        )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Validar pre\u00e7os")
        box.setText("Validar pre\u00e7os de que obras?")
        btn_minhas = box.addButton(
            f"S\u00f3 as minhas ({nome_login})" if nome_login else "S\u00f3 as minhas",
            QMessageBox.ButtonRole.AcceptRole,
        )
        btn_todas = box.addButton(
            "Todos os utilizadores",
            QMessageBox.ButtonRole.AcceptRole,
        )
        box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(btn_minhas)
        box.exec()
        clicado = box.clickedButton()
        if clicado is None or clicado not in (btn_minhas, btn_todas):
            return
        responsavel = nome_login if clicado is btn_minhas else None

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.atualizado_label.setText("A consultar pre\u00e7os no PHC/Streamlit...")
        QApplication.processEvents()
        try:
            with SessionLocal() as session:
                diffs = detetar_diferencas_preco(
                    session,
                    responsavel=responsavel,
                )
        except Exception as exc:  # ligacao/SQL/config PHC/Streamlit
            QMessageBox.warning(
                self,
                "Validar pre\u00e7os",
                self._mensagem_erro_phc(exc),
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        if not diffs:
            QMessageBox.information(
                self,
                "Validar pre\u00e7os",
                "Pre\u00e7os j\u00e1 validados - sem diferen\u00e7as face ao PHC/Streamlit.",
            )
            self._carregar()
            return

        dialog = ProducaoPrecosDialog(diffs, self)
        if not dialog.exec():
            return

        atualizacoes = dialog.selecionados()
        if not atualizacoes:
            return

        current_user_id = (
            app_session.current_user.id
            if app_session.current_user is not None
            else None
        )
        try:
            with SessionLocal() as session:
                n = aplicar_precos(
                    session,
                    atualizacoes,
                    current_user_id=current_user_id,
                )
        except SQLAlchemyError:
            QMessageBox.warning(
                self,
                "Validar pre\u00e7os",
                "N\u00e3o foi poss\u00edvel atualizar os pre\u00e7os.",
            )
            return

        self._carregar()
        QMessageBox.information(
            self,
            "Validar pre\u00e7os",
            f"{n} obra(s) atualizada(s) com pre\u00e7o externo.",
        )

    @staticmethod
    def _mensagem_erro_fonte(exc, fonte: str):
        texto = str(exc)
        if fonte == "PHC" and (
            "Configuracao PHC" in texto or "Configura\u00e7\u00e3o PHC" in texto
        ):
            return (
                "PHC n\u00e3o configurado. Configure a liga\u00e7\u00e3o em "
                "Configura\u00e7\u00f5es -> Caminhos/PHC."
            )
        if fonte == "Streamlit" and (
            "Configuracao Streamlit" in texto
            or "Configura\u00e7\u00e3o Streamlit" in texto
        ):
            return (
                "Streamlit n\u00e3o configurado. Configure a liga\u00e7\u00e3o em "
                "Configura\u00e7\u00f5es -> Caminhos/PHC."
            )
        return f"N\u00e3o foi poss\u00edvel consultar {fonte}: {texto}"

    @staticmethod
    def _mensagem_erro_phc(exc):
        return PontoSituacaoPage._mensagem_erro_fonte(exc, "PHC")

    def _texto_atualizado(self, dados) -> str:
        filtros = []
        pesquisa = self.campo_pesquisa.texto().strip()
        if pesquisa:
            filtros.append(f"Pesquisa={pesquisa}")
        if self._combo_valor(self.utilizador_combo):
            filtros.append(f"Utilizador={self._combo_valor(self.utilizador_combo)}")
        if self._combo_valor(self.cliente_combo):
            filtros.append(f"Cliente={self._combo_valor(self.cliente_combo)}")
        if self._combo_valor(self.estado_combo):
            filtros.append(f"Estado={self._combo_valor(self.estado_combo)}")

        texto = f"{dados.total} obras \u00b7 atualizado {dados.hoje.strftime('%d-%m-%Y')}"
        if filtros:
            texto += " \u00b7 filtros: " + ", ".join(filtros)
        return texto

    def _limpar_filtros(self) -> None:
        widgets = (
            self.campo_pesquisa,
            self.utilizador_combo,
            self.cliente_combo,
            self.estado_combo,
        )
        estados_sinais = [(widget, widget.blockSignals(True)) for widget in widgets]
        self.campo_pesquisa.limpar()
        for combo in (self.utilizador_combo, self.cliente_combo, self.estado_combo):
            if combo.count():
                combo.setCurrentIndex(0)
        for widget, estado_anterior in estados_sinais:
            widget.blockSignals(estado_anterior)
        self._carregar()
        self._pos_filtros()

    def _atualizar_combos(self, dados) -> None:
        self._popular_combo(
            self.utilizador_combo,
            [valor for valor, _qt in dados.por_responsavel],
        )
        self._popular_combo(
            self.cliente_combo,
            [valor for valor, _qt in dados.por_cliente],
        )
        self._popular_combo(
            self.estado_combo,
            self._combinar_valores(
                list(ESTADOS_PRODUCAO),
                [valor for valor, _qt in dados.por_estado],
            ),
        )

    def _substituir(self, box, widget) -> None:
        while box.count():
            item = box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        box.addWidget(widget)

    def _grafico_estado(self, dados):
        serie = QPieSeries()
        serie.setHoleSize(0.45)
        for estado, qt in dados.por_estado:
            fatia = serie.append(f"{estado} ({qt})", qt)
            fatia.setBrush(QColor(CORES_ESTADO.get(estado, tema.CINZA_CASTANHO)))
            fatia.setLabelVisible(True)

        chart = QChart()
        chart.addSeries(serie)
        chart.setTitle("Obras por estado")
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        return self._chart_view(chart)

    def _grafico_responsavel(self, dados):
        top = dados.por_responsavel[:10]
        barset = QBarSet("Obras")
        categorias = []
        for responsavel, qt in top:
            barset.append(qt)
            categorias.append(responsavel)
        barset.setColor(QColor(tema.CASTANHO_MEDIO))

        serie = QBarSeries()
        serie.append(barset)

        chart = QChart()
        chart.addSeries(serie)
        chart.setTitle("Obras por respons\u00e1vel")

        eixo_x = QBarCategoryAxis()
        eixo_x.append(categorias)
        chart.addAxis(eixo_x, Qt.AlignmentFlag.AlignBottom)
        serie.attachAxis(eixo_x)

        eixo_y = QValueAxis()
        # Sem dados, applyNiceNumbers() calcula um intervalo [nan, nan] e o Qt
        # avisa. Fixa-se um intervalo trivial nesse caso.
        maximo = max((qt for _, qt in top), default=0)
        if maximo > 0:
            eixo_y.setRange(0, maximo)
            eixo_y.applyNiceNumbers()
        else:
            eixo_y.setRange(0, 1)
        chart.addAxis(eixo_y, Qt.AlignmentFlag.AlignLeft)
        serie.attachAxis(eixo_y)

        chart.legend().setVisible(False)
        return self._chart_view(chart)

    def _grafico_clientes(self, dados):
        top = dados.por_cliente[:8]
        barset = QBarSet("Obras")
        categorias = []
        for cliente, qt in reversed(top):
            barset.append(qt)
            nome = cliente if len(cliente) <= 24 else cliente[:23] + "..."
            categorias.append(nome)
        barset.setColor(QColor("#1BAF7A"))

        serie = QHorizontalBarSeries()
        serie.append(barset)

        chart = QChart()
        chart.addSeries(serie)
        chart.setTitle("Top clientes (n\u00ba de obras)")

        eixo_y = QBarCategoryAxis()
        eixo_y.append(categorias)
        chart.addAxis(eixo_y, Qt.AlignmentFlag.AlignLeft)
        serie.attachAxis(eixo_y)

        eixo_x = QValueAxis()
        maximo = max((qt for _, qt in top), default=0)
        if maximo > 0:
            eixo_x.setRange(0, maximo)
            eixo_x.applyNiceNumbers()
        else:
            eixo_x.setRange(0, 1)
        chart.addAxis(eixo_x, Qt.AlignmentFlag.AlignBottom)
        serie.attachAxis(eixo_x)

        chart.legend().setVisible(False)
        return self._chart_view(chart)

    @staticmethod
    def _chart_view(chart):
        chart.setBackgroundVisible(False)
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setMinimumHeight(220)
        return view

    def _popular_combo(self, combo, valores) -> None:
        atual = combo.currentText() or "Todos"
        estado_anterior = combo.blockSignals(True)
        combo.clear()
        combo.addItem("Todos")
        for valor in valores:
            if valor and valor not in ("(sem resp)", "(sem cliente)", "(sem estado)"):
                combo.addItem(valor)

        indice = combo.findText(atual)
        combo.setCurrentIndex(indice if indice >= 0 else 0)
        combo.blockSignals(estado_anterior)

    @staticmethod
    def _combo_valor(combo):
        valor = combo.currentText().strip()
        return None if (not valor or valor == "Todos") else valor

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
