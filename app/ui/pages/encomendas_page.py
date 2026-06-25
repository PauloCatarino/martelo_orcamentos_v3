"""Encomendas page: PHC orders (read-only) + placeholders for next phases."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.db.session import SessionLocal
from app.services.encomendas_phc_service import query_encomendas_phc
from app.services.streamlit_sql_service import (
    query_encomendas_cliente_final,
    query_itens_encomenda,
)
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.estado_splitter import ligar_persistencia_splitter
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class EncomendasPHCTab(QWidget):
    """Read-only PHC orders tab (loaded on demand from the PHC database)."""

    # (titulo da coluna, chave devolvida pelo servico/SQL)
    _COLUNAS = (
        ("Cliente", "Cliente"),
        ("Cliente Abreviado", "Cliente_Abreviado"),
        ("Enc Nº", "Enc_No"),
        ("Num PHC", "Num_PHC"),
        ("Ref PHC", "Ref_PHC"),
        ("Telefone", "Telefone"),
        ("Ref Cliente", "Ref_Cliente"),
        ("Descrição Artigo", "Descricao_Artigo"),
        ("Data Encomenda", "Data_Encomenda"),
        ("Data Entrega", "Data_Entrega"),
    )
    TABLE_HEADERS = [titulo for titulo, _chave in _COLUNAS]

    def __init__(self) -> None:
        super().__init__()

        self._linhas: list[dict] = []

        self.ano_spin = QSpinBox()
        self.ano_spin.setRange(1900, 2200)
        self.ano_spin.setValue(2026)
        self.ano_spin.setToolTip(
            "Carregar encomendas com data igual ou posterior a 01-01 deste ano"
        )

        self.max_linhas_spin = QSpinBox()
        self.max_linhas_spin.setRange(0, 100000)
        self.max_linhas_spin.setValue(5000)
        self.max_linhas_spin.setToolTip(
            "Limite de linhas a carregar (0 = sem limite)"
        )

        self.carregar_button = QPushButton("Carregar Encomendas (PHC)")
        self.carregar_button.setToolTip(
            "Consultar as encomendas no PHC (só leitura) com os filtros acima"
        )
        self.carregar_button.clicked.connect(self._carregar)

        self.campo_pesquisa = CampoPesquisa()
        self.campo_pesquisa.setToolTip(
            "Filtrar a tabela já carregada (vários termos: espaço ou %)"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)
        self.campo_pesquisa.limpar_clicado.connect(self._render)

        filtros_layout = QHBoxLayout()
        filtros_layout.addWidget(QLabel("Ano mínimo"))
        filtros_layout.addWidget(self.ano_spin)
        filtros_layout.addWidget(QLabel("Máx. linhas"))
        filtros_layout.addWidget(self.max_linhas_spin)
        filtros_layout.addWidget(self.carregar_button)
        filtros_layout.addSpacing(12)
        filtros_layout.addWidget(self.campo_pesquisa, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("encomendasStatus")

        self.table = self._criar_tabela()

        self.footer_label = QLabel("")
        self.footer_label.setObjectName("encomendasFooter")
        self.footer_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(filtros_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.footer_label)

    def _criar_tabela(self) -> QTableWidget:
        table = QTableWidget(0, len(self.TABLE_HEADERS))
        table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        ligar_persistencia_larguras(table, "encomendas_phc")
        return table

    def _carregar(self) -> None:
        """Load PHC orders into memory and render. Errors go to the status label."""
        self.status_label.setText("A carregar do PHC...")
        self.carregar_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        try:
            with SessionLocal() as session:
                linhas = query_encomendas_phc(
                    session,
                    ano_minimo=self.ano_spin.value(),
                    max_linhas=self.max_linhas_spin.value(),
                )
        except Exception as exc:  # ligação/SQL/config externos
            self._linhas = []
            self._render()
            self.status_label.setText(self._mensagem_erro(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.carregar_button.setEnabled(True)

        self._linhas = list(linhas)
        self._render()
        self.status_label.setText(
            f"{len(self._linhas)} encomendas carregadas do PHC."
        )

    def _render(self, *_args) -> None:
        """Render the loaded rows applying the in-memory search filter."""
        filtradas = self._filtrar(self._linhas, self.campo_pesquisa.texto())
        self._preencher_tabela(filtradas)
        self.footer_label.setText(f"{len(filtradas)} de {len(self._linhas)}")

    def _preencher_tabela(self, linhas: list[dict]) -> None:
        self.table.setRowCount(len(linhas))
        for row_index, linha in enumerate(linhas):
            for column_index, (_titulo, chave) in enumerate(self._COLUNAS):
                valor = self._valor(linha, chave)
                item = QTableWidgetItem(valor)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                if valor:
                    item.setToolTip(valor)
                self.table.setItem(row_index, column_index, item)

    def _filtrar(self, linhas: list[dict], texto: str) -> list[dict]:
        """Multi-term, case-insensitive filter over the visible columns."""
        termos = [
            termo
            for termo in re.split(r"[\s%]+", (texto or "").strip().lower())
            if termo
        ]
        if not termos:
            return list(linhas or [])

        resultado = []
        for linha in linhas or []:
            haystack = " ".join(
                self._valor(linha, chave) for _titulo, chave in self._COLUNAS
            ).lower()
            if all(termo in haystack for termo in termos):
                resultado.append(linha)
        return resultado

    @staticmethod
    def _valor(linha: dict, chave: str) -> str:
        valor = linha.get(chave)
        return "" if valor is None else str(valor).strip()

    @staticmethod
    def _mensagem_erro(exc: Exception) -> str:
        texto = str(exc)
        if "Configuracao PHC" in texto or "Configuração PHC" in texto:
            return (
                "PHC não configurado. Configure a ligação em "
                "Configurações → Caminhos/PHC."
            )
        return f"Não foi possível carregar do PHC: {texto}"


class EncomendasClienteFinalTab(QWidget):
    """Read-only Cliente Final orders (Streamlit SQL Server), master-detail."""

    # (titulo da coluna, chave devolvida pelo servico/SQL) — tabela MASTER
    _COLUNAS_MASTER = (
        ("Número", "Numero"),
        ("Ano", "Ano"),
        ("Cliente", "Cliente"),
        ("Cliente Abreviado", "Cliente_Abre"),
        ("Contacto", "Contacto"),
        ("Ref Cliente", "RefCliente"),
        ("Data Receção", "DataRecepcao"),
        ("Responsável", "Responsavel"),
        ("Data Entrega", "DataEntrega"),
        ("Prazo Obrig.", "PrazoObrigatorio"),
        ("Status", "Status"),
        ("Nº Paletes", "NumPaletes"),
        ("Tipo Paletes", "TipoPaletes"),
        ("Formato Palete", "FormatoPalete"),
        ("Montagem", "ExisteMontagem"),
        ("Anulada", "Anulada"),
        ("Observações", "Observacoes"),
    )
    MASTER_HEADERS = [titulo for titulo, _chave in _COLUNAS_MASTER]

    # (titulo da coluna, chave devolvida pelo servico/SQL) — tabela DETAIL
    _COLUNAS_DETAIL = (
        ("Ref Obra", "RefObra"),
        ("Referência", "Referencia"),
        ("Designação", "Designacao"),
        ("X", "X"),
        ("Y", "Y"),
        ("Z", "Z"),
        ("Quantidade", "Quantidade"),
        ("Unidade", "Unidade"),
        ("Venda", "Venda"),
        ("Valor Venda", "ValorVenda"),
        ("Unid. Alt", "UnidadeAlternativa"),
        ("Qtd Alt", "QuantidadeAlternativa"),
    )
    DETAIL_HEADERS = [titulo for titulo, _chave in _COLUNAS_DETAIL]

    def __init__(self) -> None:
        super().__init__()

        self._encomendas: list[dict] = []
        self._encomendas_by_row: dict[int, dict] = {}

        self.ano_spin = QSpinBox()
        self.ano_spin.setRange(1900, 2200)
        self.ano_spin.setValue(2026)
        self.ano_spin.setToolTip(
            "Carregar encomendas com Ano igual ou posterior a este"
        )

        self.max_encomendas_spin = QSpinBox()
        self.max_encomendas_spin.setRange(0, 1000000)
        self.max_encomendas_spin.setValue(5000)
        self.max_encomendas_spin.setToolTip(
            "Limite de encomendas a carregar (0 = sem limite)"
        )

        self.max_itens_spin = QSpinBox()
        self.max_itens_spin.setRange(0, 1000000)
        self.max_itens_spin.setValue(20000)
        self.max_itens_spin.setToolTip(
            "Limite de itens por encomenda a carregar (0 = sem limite)"
        )

        self.carregar_button = QPushButton("Carregar Encomendas (Cliente Final)")
        self.carregar_button.setToolTip(
            "Consultar as encomendas Cliente Final no Streamlit (só leitura)"
        )
        self.carregar_button.clicked.connect(self._carregar)

        self.campo_pesquisa = CampoPesquisa()
        self.campo_pesquisa.setToolTip(
            "Filtrar a tabela de encomendas já carregada (vários termos: espaço ou %)"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self._render_master)
        self.campo_pesquisa.limpar_clicado.connect(self._render_master)

        filtros_layout = QHBoxLayout()
        filtros_layout.addWidget(QLabel("Ano mínimo"))
        filtros_layout.addWidget(self.ano_spin)
        filtros_layout.addWidget(QLabel("Máx. encomendas"))
        filtros_layout.addWidget(self.max_encomendas_spin)
        filtros_layout.addWidget(QLabel("Máx. itens"))
        filtros_layout.addWidget(self.max_itens_spin)
        filtros_layout.addWidget(self.carregar_button)
        filtros_layout.addSpacing(12)
        filtros_layout.addWidget(self.campo_pesquisa, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("encomendasCfStatus")

        # MASTER
        self.master_table = self._nova_tabela(
            self.MASTER_HEADERS, "encomendas_cf_master"
        )
        self.master_table.itemSelectionChanged.connect(self._on_master_select)
        self.master_footer = QLabel("")
        self.master_footer.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 2px;"
        )
        master_group = QGroupBox("Encomendas")
        master_group.setStyleSheet(
            f"QGroupBox {{ color: {tema.CASTANHO_ESCURO}; font-weight: bold; }}"
        )
        master_layout = QVBoxLayout(master_group)
        master_layout.setContentsMargins(8, 12, 8, 8)
        master_layout.addWidget(self.master_table, stretch=1)
        master_layout.addWidget(self.master_footer)

        # DETAIL
        self.detail_table = self._nova_tabela(
            self.DETAIL_HEADERS, "encomendas_cf_itens"
        )
        self.detail_group = QGroupBox("Itens Encomenda (selecione uma encomenda)")
        self.detail_group.setStyleSheet(
            f"QGroupBox {{ color: {tema.CASTANHO_ESCURO}; font-weight: bold; }}"
        )
        detail_layout = QVBoxLayout(self.detail_group)
        detail_layout.setContentsMargins(8, 12, 8, 8)
        detail_layout.addWidget(self.detail_table, stretch=1)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(master_group)
        self.splitter.addWidget(self.detail_group)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        if not ligar_persistencia_splitter(self.splitter, "encomendas_cliente_final"):
            self.splitter.setSizes([360, 320])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(filtros_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.splitter, stretch=1)

    def _nova_tabela(self, headers: list[str], chave_larguras: str) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        ligar_persistencia_larguras(table, chave_larguras)
        return table

    def _carregar(self) -> None:
        """Load Cliente Final orders into the master table. Errors -> status."""
        self.status_label.setText("A carregar do Streamlit...")
        self.carregar_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        try:
            with SessionLocal() as session:
                encomendas = query_encomendas_cliente_final(
                    session,
                    ano_minimo=self.ano_spin.value(),
                    max_linhas=self.max_encomendas_spin.value(),
                )
        except Exception as exc:  # ligação/SQL/config externos
            self._encomendas = []
            self._render_master()
            self._limpar_detail()
            self.status_label.setText(self._mensagem_erro(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.carregar_button.setEnabled(True)

        self._encomendas = list(encomendas)
        self._render_master()
        self._limpar_detail()
        self.status_label.setText(
            f"{len(self._encomendas)} encomendas carregadas (Cliente Final)."
        )

    def _render_master(self, *_args) -> None:
        """Render the loaded orders applying the in-memory search filter."""
        filtradas = self._filtrar(self._encomendas, self.campo_pesquisa.texto())
        self._preencher_master(filtradas)

    def _preencher_master(self, encomendas: list[dict]) -> None:
        self._encomendas_by_row = {}
        estado = self.master_table.blockSignals(True)
        self.master_table.setRowCount(len(encomendas))
        for row_index, encomenda in enumerate(encomendas):
            self._encomendas_by_row[row_index] = encomenda
            for column_index, (_titulo, chave) in enumerate(self._COLUNAS_MASTER):
                valor = self._valor(encomenda, chave)
                item = QTableWidgetItem(valor)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                if valor:
                    item.setToolTip(valor)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, encomenda.get("Id"))
                self.master_table.setItem(row_index, column_index, item)
        self.master_table.blockSignals(estado)
        self.master_footer.setText(
            f"{len(encomendas)} de {len(self._encomendas)}"
        )

    def _on_master_select(self) -> None:
        row = self.master_table.currentRow()
        encomenda = self._encomendas_by_row.get(row)
        if encomenda is None:
            return
        self._carregar_itens(encomenda)

    def _carregar_itens(self, encomenda: dict) -> None:
        encomenda_id = encomenda.get("Id")
        numero = self._valor(encomenda, "Numero")
        if encomenda_id is None:
            return

        self.detail_group.setTitle(f"Itens Encomenda (Nº {numero})")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        try:
            with SessionLocal() as session:
                itens = query_itens_encomenda(
                    session,
                    encomenda_id=int(encomenda_id),
                    max_itens=self.max_itens_spin.value(),
                )
        except Exception as exc:  # ligação/SQL/config externos
            self._preencher_detail([])
            self.status_label.setText(self._mensagem_erro(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()

        self._preencher_detail(itens)
        self.status_label.setText(f"Encomenda Nº {numero}: {len(itens)} itens.")

    def _preencher_detail(self, itens: list[dict]) -> None:
        self.detail_table.setRowCount(len(itens))
        for row_index, item_dict in enumerate(itens):
            for column_index, (_titulo, chave) in enumerate(self._COLUNAS_DETAIL):
                valor = self._valor(item_dict, chave)
                cell = QTableWidgetItem(valor)
                cell.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                if valor:
                    cell.setToolTip(valor)
                self.detail_table.setItem(row_index, column_index, cell)

    def _limpar_detail(self) -> None:
        self.detail_table.setRowCount(0)
        self.detail_group.setTitle("Itens Encomenda (selecione uma encomenda)")

    def _filtrar(self, encomendas: list[dict], texto: str) -> list[dict]:
        """Multi-term, case-insensitive filter over the master columns."""
        termos = [
            termo
            for termo in re.split(r"[\s%]+", (texto or "").strip().lower())
            if termo
        ]
        if not termos:
            return list(encomendas or [])

        resultado = []
        for encomenda in encomendas or []:
            haystack = " ".join(
                self._valor(encomenda, chave)
                for _titulo, chave in self._COLUNAS_MASTER
            ).lower()
            if all(termo in haystack for termo in termos):
                resultado.append(encomenda)
        return resultado

    @staticmethod
    def _valor(linha: dict, chave: str) -> str:
        valor = linha.get(chave)
        return "" if valor is None else str(valor).strip()

    @staticmethod
    def _mensagem_erro(exc: Exception) -> str:
        texto = str(exc)
        if "Configuracao Streamlit" in texto or "Configuração Streamlit" in texto:
            return (
                "Streamlit não configurado. Defina servidor/password em "
                "Configurações → Caminhos (grupo Streamlit)."
            )
        return f"Não foi possível carregar do Streamlit: {texto}"


class EncomendasPage(QWidget):
    """Encomendas page: PHC orders (implemented) + two next-phase placeholders."""

    def __init__(self) -> None:
        super().__init__()

        self.cabecalho = BarraCabecalho(
            "Encomendas PHC",
            ["Encomendas do PHC e Cliente Final (consulta)"],
        )

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(tema.ESTILO_ABAS)

        self.encomendas_phc_tab = EncomendasPHCTab()
        self.tabs.addTab(self.encomendas_phc_tab, "Encomendas PHC")
        self.encomendas_cf_tab = EncomendasClienteFinalTab()
        self.tabs.addTab(self.encomendas_cf_tab, "Encomendas Cliente Final")
        self.tabs.addTab(
            self._placeholder("Em desenvolvimento"),
            "Diagnóstico PHC",
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addWidget(self.tabs, stretch=1)

    @staticmethod
    def _placeholder(texto: str) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        label = QLabel(texto)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {tema.CASTANHO_ESCURO};")
        panel_layout.addWidget(label)
        return panel
