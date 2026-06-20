"""Customers page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.clientes_lista import filtrar_clientes
from app.repositories.cliente_repository import ClienteListaResumo, ClienteRepository
from app.services.cliente_phc_sync_service import ClientePhcSyncService
from app.services.cliente_temporario_service import (
    ClienteEmUsoError,
    ClienteTemporarioService,
    DadosClienteTemporario,
)
from app.services import phc_sql
from app.ui import tema
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class ClientesPage(QWidget):
    """Customers page with temporary and PHC customer lists."""

    TABLE_HEADERS = [
        "Nome",
        "Simplex",
        "Morada",
        "Email",
        "WEB",
        "Telefone",
        "Telem\u00f3vel",
        "Num PHC",
        "Info 1",
        "Info 2",
    ]
    COLUMN_WIDTHS = {
        "Nome": 220,
        "Simplex": 160,
        "Morada": 260,
        "Email": 220,
        "WEB": 220,
        "Telefone": 110,
        "Telem\u00f3vel": 110,
        "Num PHC": 90,
        "Info 1": 180,
        "Info 2": 180,
    }

    def __init__(self) -> None:
        super().__init__()

        self._todos: list[ClienteListaResumo] = []
        self._linhas: list[ClienteListaResumo] = []
        self._phc_todos: list[ClienteListaResumo] = []
        self._cliente_id: int | None = None

        title = QLabel("Clientes")
        title.setObjectName("pageTitle")

        tabs = QTabWidget()
        tabs.addTab(self._criar_tab_temporarios(), "Clientes Tempor\u00e1rios")
        tabs.addTab(self._criar_tab_phc(), "Clientes PHC")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(tabs, stretch=1)
        self.setLayout(layout)

        self.carregar()
        self.carregar_phc()

    def _criar_tab_temporarios(self) -> QWidget:
        tab = QWidget()

        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar \u2014 espa\u00e7o ou % para v\u00e1rios termos\u2026"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)
        self.campo_pesquisa.limpar_clicado.connect(self._render)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.campo_pesquisa)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("clientesStatus")

        self.new_button = QPushButton("Novo")
        self.new_button.clicked.connect(self._on_novo)
        self.save_button = QPushButton("Guardar")
        self.save_button.clicked.connect(self._on_guardar)
        self.delete_button = QPushButton("Eliminar")
        self.delete_button.clicked.connect(self._on_eliminar)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.save_button)
        actions_layout.addWidget(self.delete_button)
        actions_layout.addStretch()

        form_group = QGroupBox("Dados do Cliente")
        form_layout = QGridLayout()
        self.ed_nome = QLineEdit()
        self.ed_simplex = QLineEdit()
        self.ed_simplex.setPlaceholderText("Gerado do nome se vazio")
        self.ed_num_phc = QLineEdit()
        self.ed_telefone = QLineEdit()
        self.ed_telemovel = QLineEdit()
        self.ed_email = QLineEdit()
        self.ed_web = QLineEdit()
        self.ed_morada = QTextEdit()
        self.ed_morada.setFixedHeight(48)
        self.ed_info1 = QTextEdit()
        self.ed_info1.setFixedHeight(60)
        self.ed_info2 = QTextEdit()
        self.ed_info2.setFixedHeight(60)

        form_layout.addWidget(QLabel("Nome"), 0, 0)
        form_layout.addWidget(self.ed_nome, 0, 1)
        form_layout.addWidget(QLabel("Simplex"), 0, 2)
        form_layout.addWidget(self.ed_simplex, 0, 3)
        form_layout.addWidget(QLabel("Num PHC"), 1, 0)
        form_layout.addWidget(self.ed_num_phc, 1, 1)
        form_layout.addWidget(QLabel("Telefone"), 1, 2)
        form_layout.addWidget(self.ed_telefone, 1, 3)
        form_layout.addWidget(QLabel("Telem\u00f3vel"), 2, 0)
        form_layout.addWidget(self.ed_telemovel, 2, 1)
        form_layout.addWidget(QLabel("E-Mail"), 2, 2)
        form_layout.addWidget(self.ed_email, 2, 3)
        form_layout.addWidget(QLabel("P\u00e1gina WEB"), 3, 0)
        form_layout.addWidget(self.ed_web, 3, 1, 1, 3)
        form_layout.addWidget(QLabel("Morada"), 4, 0)
        form_layout.addWidget(self.ed_morada, 4, 1, 1, 3)
        form_layout.addWidget(QLabel("Info 1"), 5, 0)
        form_layout.addWidget(self.ed_info1, 5, 1, 1, 3)
        form_layout.addWidget(QLabel("Info 2"), 6, 0)
        form_layout.addWidget(self.ed_info2, 6, 1, 1, 3)
        form_layout.setColumnStretch(1, 1)
        form_layout.setColumnStretch(3, 1)
        form_group.setLayout(form_layout)

        self.table = self._nova_tabela_clientes()
        self.table.itemSelectionChanged.connect(self._on_selecao)
        ligar_persistencia_larguras(self.table, "clientes_temporarios")

        self.footer_label = QLabel("")
        self.footer_label.setObjectName("clientesFooter")
        self.footer_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addLayout(toolbar)
        layout.addWidget(self.status_label)
        layout.addLayout(actions_layout)
        layout.addWidget(form_group)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.footer_label)
        tab.setLayout(layout)

        return tab

    def _criar_tab_phc(self) -> QWidget:
        tab = QWidget()

        info = QLabel(
            "Clientes PHC (oficiais). S\u00e3o criados no PHC e aqui apenas "
            "consultados (s\u00f3 leitura). Use \u00abAtualizar PHC\u00bb para "
            "sincronizar a partir do PHC."
        )
        info.setObjectName("pageSubtitle")
        info.setWordWrap(True)

        self.phc_campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar \u2014 espa\u00e7o ou % para v\u00e1rios termos\u2026"
        )
        self.phc_campo_pesquisa.pesquisa_mudou.connect(self._render_phc)
        self.phc_campo_pesquisa.limpar_clicado.connect(self._render_phc)

        self.phc_refresh_button = QPushButton("Atualizar")
        self.phc_refresh_button.clicked.connect(self.carregar_phc)
        self.phc_test_button = QPushButton("Testar liga\u00e7\u00e3o PHC")
        self.phc_test_button.clicked.connect(self._testar_ligacao_phc)
        self.phc_sync_button = QPushButton("Atualizar PHC")
        self.phc_sync_button.clicked.connect(self._sincronizar_phc)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.phc_campo_pesquisa)
        toolbar.addWidget(self.phc_refresh_button)
        toolbar.addWidget(self.phc_test_button)
        toolbar.addWidget(self.phc_sync_button)
        toolbar.addStretch()

        self.phc_status_label = QLabel("")
        self.phc_status_label.setObjectName("clientesStatus")

        self.phc_table = self._nova_tabela_clientes()
        ligar_persistencia_larguras(self.phc_table, "clientes_phc")

        self.phc_footer_label = QLabel("")
        self.phc_footer_label.setObjectName("clientesFooter")
        self.phc_footer_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(info)
        layout.addLayout(toolbar)
        layout.addWidget(self.phc_status_label)
        layout.addWidget(self.phc_table, stretch=1)
        layout.addWidget(self.phc_footer_label)
        tab.setLayout(layout)

        return tab

    def _nova_tabela_clientes(self) -> QTableWidget:
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
        self._aplicar_larguras_colunas(table)
        return table

    def _aplicar_larguras_colunas(self, table: QTableWidget) -> None:
        for column_index, header in enumerate(self.TABLE_HEADERS):
            largura = self.COLUMN_WIDTHS.get(header)
            if largura is not None:
                table.setColumnWidth(column_index, largura)

    @staticmethod
    def _povoar_tabela(
        table: QTableWidget, clientes: list[ClienteListaResumo]
    ) -> None:
        table.setRowCount(len(clientes))

        for row_index, cliente in enumerate(clientes):
            values = [
                cliente.nome,
                cliente.nome_simplex or "",
                cliente.morada or "",
                cliente.email or "",
                cliente.pagina_web or "",
                cliente.telefone or "",
                cliente.telemovel or "",
                cliente.num_cliente_phc or "",
                cliente.info_1 or "",
                cliente.info_2 or "",
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                if value:
                    item.setToolTip(value)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, cliente.id)
                table.setItem(row_index, column_index, item)

    def carregar(self) -> None:
        """Load temporary customers from the database."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                clientes = ClienteRepository(session).list_temporarios()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os clientes.")
            return

        self._todos = list(clientes)
        self._render()

        if not self._todos:
            self.status_label.setText("Sem clientes temporarios para mostrar.")

    def carregar_phc(self) -> None:
        """Load PHC customers from the local database."""
        self.phc_table.setRowCount(0)
        self.phc_status_label.clear()

        try:
            with SessionLocal() as session:
                clientes = ClienteRepository(session).list_phc()
        except SQLAlchemyError:
            self.phc_status_label.setText("Nao foi possivel carregar os clientes PHC.")
            return

        self._phc_todos = list(clientes)
        self._render_phc()

        if not self._phc_todos:
            self.phc_status_label.setText("Sem clientes PHC para mostrar.")

    def _render(self, *_args) -> None:
        """Render the in-memory list using the current search."""
        filtrados = filtrar_clientes(self._todos, texto=self.campo_pesquisa.texto())
        self._preencher_tabela(filtrados)
        self.footer_label.setText(f"{len(filtrados)} clientes")

    def _render_phc(self, *_args) -> None:
        """Render the PHC in-memory list using the current search."""
        filtrados = filtrar_clientes(
            self._phc_todos, texto=self.phc_campo_pesquisa.texto()
        )
        self._povoar_tabela(self.phc_table, filtrados)
        self.phc_footer_label.setText(f"{len(filtrados)} clientes")

    def _testar_ligacao_phc(self) -> None:
        """Test the read-only PHC connection and show the dbo.CL row count."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with SessionLocal() as session:
                total = phc_sql.contar_clientes_phc(session)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self,
                "Testar liga\u00e7\u00e3o PHC",
                f"N\u00e3o foi poss\u00edvel ligar ao PHC:\n\n{exc}",
            )
            return

        QApplication.restoreOverrideCursor()
        QMessageBox.information(
            self,
            "Testar liga\u00e7\u00e3o PHC",
            f"Liga\u00e7\u00e3o OK (s\u00f3 leitura).\n\n{total} clientes em dbo.CL.",
        )

    def _sincronizar_phc(self) -> None:
        """Import/update PHC customers (read-only on PHC; writes only to Martelo)."""
        resposta = QMessageBox.question(
            self,
            "Atualizar PHC",
            "Isto vai importar/atualizar os clientes a partir do PHC (dbo.CL).\n\n"
            "No PHC \u00e9 apenas LEITURA; a escrita \u00e9 s\u00f3 na base de dados do Martelo.\n\n"
            "Continuar?",
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with SessionLocal() as session:
                resumo = ClientePhcSyncService(session).sincronizar()
        except Exception as exc:  # liga\u00e7\u00e3o/SQL/config externos
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self,
                "Atualizar PHC",
                f"N\u00e3o foi poss\u00edvel atualizar a partir do PHC:\n\n{exc}",
            )
            return
        QApplication.restoreOverrideCursor()

        self.carregar_phc()
        QMessageBox.information(
            self,
            "Atualizar PHC",
            "Atualiza\u00e7\u00e3o conclu\u00edda.\n\n"
            f"Total no PHC: {resumo.total_phc}\n"
            f"Criados: {resumo.criados}\n"
            f"Atualizados: {resumo.atualizados}\n"
            f"Ignorados: {resumo.ignorados}",
        )

    def _preencher_tabela(self, clientes: list[ClienteListaResumo]) -> None:
        """Fill the table with customer read models."""
        self._linhas = list(clientes)
        self._povoar_tabela(self.table, self._linhas)

    def _on_selecao(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._linhas):
            return

        resumo = self._linhas[row]
        self._cliente_id = resumo.id
        self.ed_nome.setText(resumo.nome or "")
        self.ed_simplex.setText(resumo.nome_simplex or "")
        self.ed_num_phc.setText(resumo.num_cliente_phc or "")
        self.ed_telefone.setText(resumo.telefone or "")
        self.ed_telemovel.setText(resumo.telemovel or "")
        self.ed_email.setText(resumo.email or "")
        self.ed_web.setText(resumo.pagina_web or "")
        self.ed_morada.setPlainText(resumo.morada or "")
        self.ed_info1.setPlainText(resumo.info_1 or "")
        self.ed_info2.setPlainText(resumo.info_2 or "")

    def _on_novo(self) -> None:
        self._cliente_id = None
        self.table.clearSelection()
        for campo in (
            self.ed_nome,
            self.ed_simplex,
            self.ed_num_phc,
            self.ed_telefone,
            self.ed_telemovel,
            self.ed_email,
            self.ed_web,
        ):
            campo.clear()
        for campo in (self.ed_morada, self.ed_info1, self.ed_info2):
            campo.clear()
        self.ed_nome.setFocus()

    def _recolher_dados(self) -> DadosClienteTemporario:
        return DadosClienteTemporario(
            nome=self.ed_nome.text(),
            nome_simplex=self.ed_simplex.text(),
            morada=self.ed_morada.toPlainText(),
            email=self.ed_email.text(),
            pagina_web=self.ed_web.text(),
            telefone=self.ed_telefone.text(),
            telemovel=self.ed_telemovel.text(),
            num_cliente_phc=self.ed_num_phc.text(),
            info_1=self.ed_info1.toPlainText(),
            info_2=self.ed_info2.toPlainText(),
        )

    def _on_guardar(self) -> None:
        dados = self._recolher_dados()
        try:
            with SessionLocal() as session:
                servico = ClienteTemporarioService(session)
                if self._cliente_id is None:
                    resumo = servico.criar(dados)
                else:
                    resumo = servico.editar(self._cliente_id, dados)
            novo_id = resumo.id
        except ValueError as exc:
            QMessageBox.warning(self, "Dados em falta", str(exc))
            return
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel guardar o cliente.")
            return

        self.carregar()
        self._selecionar_por_id(novo_id)
        self.status_label.setText("Cliente guardado.")

    def _on_eliminar(self) -> None:
        if self._cliente_id is None:
            self.status_label.setText("Selecione um cliente para eliminar.")
            return

        resposta = QMessageBox.question(
            self,
            "Confirmar",
            "Eliminar o cliente selecionado?",
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                ClienteTemporarioService(session).eliminar(self._cliente_id)
        except ClienteEmUsoError as exc:
            QMessageBox.warning(
                self,
                "Cliente em uso",
                f"{exc}\n\nElimine/realoque os orcamentos associados antes de o apagar.",
            )
            return
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel eliminar o cliente.")
            return

        self.carregar()
        self._on_novo()
        self.status_label.setText("Cliente eliminado.")

    def _selecionar_por_id(self, cliente_id: int) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == cliente_id:
                self.table.selectRow(row)
                return
