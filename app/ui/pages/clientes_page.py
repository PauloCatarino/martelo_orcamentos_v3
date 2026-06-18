"""Customers page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from app.services.cliente_temporario_service import (
    ClienteEmUsoError,
    ClienteTemporarioService,
    DadosClienteTemporario,
)
from app.ui import tema
from app.ui.widgets.barra_pesquisa import CampoPesquisa


class ClientesPage(QWidget):
    """Customers page with temporary customers list."""

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
        self._cliente_id: int | None = None

        title = QLabel("Clientes")
        title.setObjectName("pageTitle")

        tabs = QTabWidget()
        tabs.addTab(self._criar_tab_temporarios(), "Clientes Tempor\u00e1rios")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(tabs, stretch=1)
        self.setLayout(layout)

        self.carregar()

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
        self.table.itemSelectionChanged.connect(self._on_selecao)

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

    def _render(self, *_args) -> None:
        """Render the in-memory list using the current search."""
        filtrados = filtrar_clientes(self._todos, texto=self.campo_pesquisa.texto())
        self._preencher_tabela(filtrados)
        self.footer_label.setText(f"{len(filtrados)} clientes")

    def _preencher_tabela(self, clientes: list[ClienteListaResumo]) -> None:
        """Fill the table with customer read models."""
        self._linhas = list(clientes)
        self.table.setRowCount(len(clientes))

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
                self.table.setItem(row_index, column_index, item)

    def _aplicar_larguras_colunas(self) -> None:
        for column_index, header in enumerate(self.TABLE_HEADERS):
            largura = self.COLUMN_WIDTHS.get(header)
            if largura is not None:
                self.table.setColumnWidth(column_index, largura)

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
