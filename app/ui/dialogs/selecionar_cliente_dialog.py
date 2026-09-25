"""Dialog for picking an existing customer."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.clientes_lista import filtrar_clientes
from app.domain.clientes_simplex import (
    erro_simplex_orcamento,
    simplex_demasiado_longo,
)
from app.repositories.cliente_repository import ClienteListaResumo, ClienteRepository
from app.ui import tema
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.table_item import criar_item_tabela
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class SelecionarClienteDialog(QDialog):
    """Modal dialog to search and select an existing customer."""

    TABLE_HEADERS = ["Tipo", "Nome", "Simplex", "Email", "Telefone", "Telem\u00f3vel"]

    COL_SIMPLEX = 2

    def __init__(
        self,
        parent=None,
        *,
        apenas_phc: bool = False,
        exigir_simplex: bool = False,
    ) -> None:
        """``exigir_simplex``: o cliente vai para um orçamento, por isso tem de
        ter nome abreviado — é ele que dá o nome à pasta no servidor."""
        super().__init__(parent)

        self.selected_cliente: ClienteListaResumo | None = None
        self._todos: list[ClienteListaResumo] = []
        self._linhas: list[ClienteListaResumo] = []
        self._apenas_phc = apenas_phc
        self._exigir_simplex = exigir_simplex

        self.setWindowTitle("Selecionar Cliente")
        self.setModal(True)
        self.setMinimumSize(760, 460)

        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar \u2014 espa\u00e7o ou % para v\u00e1rios termos\u2026"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)

        self.status_label = QLabel("")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        ligar_persistencia_larguras(self.table, "selecionar_cliente")
        self.table.cellDoubleClicked.connect(self._handle_double_click)

        self.select_button = QPushButton("Selecionar")
        self.select_button.setToolTip(
            "Escolher o cliente da linha selecionada (ou duplo-clique na linha)."
            + (
                "\nClientes sem nome abreviado (Simplex a ocre) ou com mais de "
                "19 caracteres (a vermelho) não podem ir para um orçamento."
                if exigir_simplex
                else ""
            )
        )
        self.select_button.clicked.connect(self._selecionar)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setToolTip("Fechar sem escolher cliente.")
        self.cancel_button.clicked.connect(self.reject)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.campo_pesquisa, stretch=1)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.select_button)
        buttons_layout.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addLayout(search_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._carregar()

    def _carregar(self) -> None:
        try:
            with SessionLocal() as session:
                repository = ClienteRepository(session)
                clientes = (
                    repository.list_phc()
                    if self._apenas_phc
                    else repository.list_todos()
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os clientes.")
            return

        self._todos = list(clientes)
        self._render()

        if not self._todos:
            self.status_label.setText("Sem clientes. Crie-os no menu Clientes.")

    def _render(self, *_args) -> None:
        filtrados = filtrar_clientes(self._todos, texto=self.campo_pesquisa.texto())
        self._linhas = list(filtrados)
        self.table.setRowCount(len(filtrados))

        for row_index, cliente in enumerate(filtrados):
            tipo = "Tempor\u00e1rio" if cliente.is_temporary else "PHC"
            values = [
                tipo,
                cliente.nome,
                cliente.nome_simplex or "",
                cliente.email or "",
                cliente.telefone or "",
                cliente.telemovel or "",
            ]
            for column_index, value in enumerate(values):
                item = criar_item_tabela(value)
                if column_index == self.COL_SIMPLEX:
                    self._marcar_simplex(item, cliente)
                self.table.setItem(row_index, column_index, item)

        if self._exigir_simplex and self._todos:
            self.status_label.setText(
                "O cliente tem de ter nome abreviado (Simplex): é ele que dá o "
                "nome à pasta do orçamento. A ocre/vermelho = por corrigir."
            )

    @staticmethod
    def _erro_simplex(cliente: ClienteListaResumo) -> str | None:
        return erro_simplex_orcamento(
            cliente.nome_simplex,
            nome_cliente=cliente.nome,
            temporario=bool(cliente.is_temporary),
        )

    def _marcar_simplex(self, item, cliente: ClienteListaResumo) -> None:
        """Ocre = sem nome abreviado; vermelho = mais de 19 caracteres."""
        erro = self._erro_simplex(cliente)
        if erro is None:
            return
        if simplex_demasiado_longo(cliente.nome_simplex):
            item.setBackground(QColor(tema.VERMELHO_SUAVE))
            item.setForeground(QColor(tema.VERMELHO_ESCURO))
        else:
            item.setBackground(QColor(tema.OCRE_SUAVE))
            item.setForeground(QColor(tema.OCRE_ESCURO))
            item.setText("(vazio)" if cliente.is_temporary else "(vazio no PHC)")
        item.setToolTip(erro)

    def _get_selected(self) -> ClienteListaResumo | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._linhas):
            return None

        return self._linhas[row]

    def _selecionar(self) -> None:
        cliente = self._get_selected()
        if cliente is None:
            self.status_label.setText("Selecione um cliente.")
            return

        erro = self._erro_simplex(cliente) if self._exigir_simplex else None
        if erro:
            self.status_label.setText(
                f"«{cliente.nome}» não tem nome abreviado válido — escolha outro "
                "ou corrija-o primeiro."
            )
            QMessageBox.warning(self, "Cliente sem nome abreviado", erro)
            return

        self.selected_cliente = cliente
        self.accept()

    def _handle_double_click(self, row: int, _column: int) -> None:
        self.table.selectRow(row)
        self._selecionar()
