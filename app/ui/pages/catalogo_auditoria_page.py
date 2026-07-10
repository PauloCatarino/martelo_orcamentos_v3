"""Read-only catalog audit results page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.catalogo_auditoria_service import (
    AVISO,
    ERRO,
    INFORMACAO,
    CatalogoAuditoriaItem,
    CatalogoAuditoriaService,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class CatalogoAuditoriaPage(QWidget):
    """Display technical findings; intentionally offers no mutation actions."""

    TABLE_HEADERS = [
        "Severidade",
        "Área",
        "Entidade",
        "Código",
        "Problema encontrado",
        "Consequência possível",
        "Sugestão",
        "Teste",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._itens: tuple[CatalogoAuditoriaItem, ...] = tuple()

        self.cabecalho = BarraCabecalho(
            "Auditoria do Catálogo",
            [
                "Análise apenas de leitura das peças, associados, operações, "
                "regras, ValueSets e módulos. Nenhum registo é corrigido, "
                "desativado ou eliminado por esta página."
            ],
        )

        self.executar_button = QPushButton("Executar auditoria")
        self.executar_button.clicked.connect(self.carregar)

        self.severidade_combo = QComboBox()
        self.severidade_combo.addItem("Todas as severidades", None)
        self.severidade_combo.addItem("Erros", ERRO)
        self.severidade_combo.addItem("Avisos", AVISO)
        self.severidade_combo.addItem("Informações", INFORMACAO)
        self.severidade_combo.currentIndexChanged.connect(self._aplicar_filtros)

        self.pesquisa_input = QLineEdit()
        self.pesquisa_input.setPlaceholderText(
            "Pesquisar peça, associado, problema, consequência ou teste..."
        )
        self.pesquisa_input.setClearButtonEnabled(True)
        self.pesquisa_input.textChanged.connect(self._aplicar_filtros)

        filtros = QHBoxLayout()
        filtros.addWidget(self.executar_button)
        filtros.addWidget(QLabel("Severidade:"))
        filtros.addWidget(self.severidade_combo)
        filtros.addWidget(self.pesquisa_input, stretch=1)

        self.resumo_label = QLabel("Auditoria ainda não executada.")
        self.resumo_label.setObjectName("catalogoAuditoriaResumo")
        self.status_label = QLabel("")
        self.status_label.setObjectName("catalogoAuditoriaStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        ligar_persistencia_larguras(self.table, "catalogo_auditoria")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(self.cabecalho)
        layout.addLayout(filtros)
        layout.addWidget(self.resumo_label)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def carregar(self) -> None:
        """Execute a fresh read-only audit and display its findings."""
        self.executar_button.setEnabled(False)
        self.status_label.setText("A analisar o catálogo...")
        try:
            with SessionLocal() as session:
                resultado = CatalogoAuditoriaService(session).executar()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível executar a auditoria.")
            return
        finally:
            self.executar_button.setEnabled(True)

        self._itens = resultado.itens
        self.resumo_label.setText(
            f"Total: {resultado.total}  |  Erros: {resultado.erros}  |  "
            f"Avisos: {resultado.avisos}  |  Informações: {resultado.informacoes}"
        )
        self._aplicar_filtros()
        self.status_label.setText(
            "Auditoria concluída. Resultados apenas de leitura; nenhuma alteração foi feita."
        )

    def _aplicar_filtros(self, *_args) -> None:
        severidade = self.severidade_combo.currentData()
        termo = self.pesquisa_input.text().strip().casefold()
        itens = [
            item
            for item in self._itens
            if (severidade is None or item.severidade == severidade)
            and (not termo or termo in self._texto_pesquisa(item).casefold())
        ]
        self._preencher_tabela(itens)

    @staticmethod
    def _texto_pesquisa(item: CatalogoAuditoriaItem) -> str:
        return " ".join(
            (
                item.severidade,
                item.area,
                item.entidade,
                item.entidade_codigo,
                item.problema,
                item.impacto,
                item.sugestao,
                item.codigo_teste,
            )
        )

    def _preencher_tabela(self, itens: list[CatalogoAuditoriaItem]) -> None:
        self.table.setRowCount(len(itens))
        cores = {
            ERRO: QColor("#f8d7da"),
            AVISO: QColor("#fff3cd"),
            INFORMACAO: QColor("#dbeafe"),
        }
        for row, item in enumerate(itens):
            valores = [
                item.severidade,
                item.area,
                item.entidade,
                item.entidade_codigo,
                item.problema,
                item.impacto,
                item.sugestao,
                item.codigo_teste,
            ]
            for column, valor in enumerate(valores):
                cell = QTableWidgetItem(str(valor or ""))
                cell.setToolTip(str(valor or ""))
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, item.entidade_id)
                    cell.setBackground(cores[item.severidade])
                self.table.setItem(row, column, cell)
        self.table.resizeRowsToContents()
