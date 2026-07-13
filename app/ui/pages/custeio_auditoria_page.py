"""Financial costing audit page."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.core.session import app_session
from app.services.custeio_auditoria_service import (
    AVISO, CRITICO, CusteioAuditoriaItem, CusteioAuditoriaService,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency


class CusteioAuditoriaPage(QWidget):
    TABLE_HEADERS = [
        "Severidade", "Categoria", "Orçamento", "Cliente", "Utilizador", "Item", "Linha",
        "Problema", "Impacto financeiro", "Ação recomendada", "Teste",
    ]

    def __init__(
        self,
        on_open_orcamento: Callable[[CusteioAuditoriaItem], None] | None = None,
    ) -> None:
        super().__init__()
        self.on_open_orcamento = on_open_orcamento
        self._itens: tuple[CusteioAuditoriaItem, ...] = ()
        self._por_linha: dict[int, CusteioAuditoriaItem] = {}
        self._resumos_por_linha = {}
        self.cabecalho = BarraCabecalho(
            "Auditoria de Custeio",
            ["Validação financeira de materiais, corte, orlagem, CNC e operações manuais. "
             "A análise é apenas de leitura e não altera orçamentos."],
        )
        self.atualizar_button = QPushButton("Atualizar análise")
        self.atualizar_button.clicked.connect(self.carregar)
        self.abrir_button = QPushButton("Abrir orçamento")
        self.abrir_button.clicked.connect(self.abrir_orcamento)
        self.abrir_button.setEnabled(False)
        self.severidade_combo = QComboBox()
        self.severidade_combo.addItems(["Todas", CRITICO, AVISO])
        self.categoria_combo = QComboBox()
        self.categoria_combo.addItem("Todas")
        self.utilizador_combo = QComboBox()
        self.utilizador_combo.addItem("Todos")
        self.pesquisa = QLineEdit()
        self.pesquisa.setClearButtonEnabled(True)
        self.pesquisa.setPlaceholderText("Pesquisar orçamento, cliente, item ou problema…")
        self.severidade_combo.currentTextChanged.connect(self._aplicar_filtros)
        self.categoria_combo.currentTextChanged.connect(self._aplicar_filtros)
        self.utilizador_combo.currentTextChanged.connect(self._aplicar_filtros)
        self.pesquisa.textChanged.connect(self._aplicar_filtros)
        filtros = QHBoxLayout()
        filtros.addWidget(self.atualizar_button)
        filtros.addWidget(self.abrir_button)
        filtros.addWidget(QLabel("Severidade"))
        filtros.addWidget(self.severidade_combo)
        filtros.addWidget(QLabel("Categoria"))
        filtros.addWidget(self.categoria_combo)
        filtros.addWidget(QLabel("Utilizador"))
        filtros.addWidget(self.utilizador_combo)
        filtros.addWidget(self.pesquisa, stretch=1)
        self.resumo = QLabel("Auditoria ainda não executada.")
        self.resumo.setStyleSheet("font-weight: bold; padding: 7px;")
        self.saude_ajuda = QLabel(
            "A Saúde considera custos, quantidades, dimensões, desperdícios, tempos, "
            "exclusões manuais e a coluna Observações produção. Observações que indiquem "
            "dados incompletos ou custo não calculado reduzem a pontuação."
        )
        self.saude_ajuda.setWordWrap(True)
        self.saude_ajuda.setStyleSheet("color: #5A3E2B; padding: 3px 7px;")
        self.status = QLabel("")
        self.saude_table = QTableWidget(0, 7)
        self.saude_table.setHorizontalHeaderLabels(
            ["Orçamento", "Cliente", "Item", "Saúde", "Críticos", "Avisos", "Impacto conhecido"]
        )
        self.saude_table.setMaximumHeight(190)
        self.saude_table.verticalHeader().setVisible(False)
        self.saude_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.saude_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.saude_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.saude_table.cellDoubleClicked.connect(self._abrir_resumo)
        ligar_persistencia_larguras(self.saude_table, "auditoria_custeio_saude")
        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.itemSelectionChanged.connect(self._atualizar_abrir)
        self.table.cellDoubleClicked.connect(lambda _r, _c: self.abrir_orcamento())
        ligar_persistencia_larguras(self.table, "auditoria_custeio")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(self.cabecalho)
        layout.addLayout(filtros)
        layout.addWidget(self.status)
        layout.addWidget(self.resumo)
        layout.addWidget(self.saude_ajuda)
        layout.addWidget(QLabel("Saúde por orçamento e item"))
        layout.addWidget(self.saude_table)
        layout.addWidget(QLabel("Ocorrências detalhadas"))
        layout.addWidget(self.table, stretch=1)

    def carregar(self) -> None:
        self.atualizar_button.setEnabled(False)
        self.status.setText("A analisar linhas de custeio…")
        try:
            with SessionLocal() as session:
                resultado = CusteioAuditoriaService(session).executar()
        except SQLAlchemyError:
            self.status.setText("Não foi possível executar a auditoria de custeio.")
            return
        finally:
            self.atualizar_button.setEnabled(True)
        self._itens = resultado.itens
        self._preencher_saude(resultado.resumos)
        self.resumo.setText(
            f"Ocorrências: {resultado.total}  |  Críticas: {resultado.criticos}  |  "
            f"Avisos: {resultado.avisos}  |  Diferença conhecida: {format_currency(resultado.impacto_conhecido)}  |  "
            "Restante impacto: por determinar até preencher tarifas/preços"
        )
        categorias = sorted({item.categoria for item in self._itens})
        atual = self.categoria_combo.currentText()
        bloqueado = self.categoria_combo.blockSignals(True)
        self.categoria_combo.clear(); self.categoria_combo.addItem("Todas")
        self.categoria_combo.addItems(categorias)
        indice = self.categoria_combo.findText(atual)
        self.categoria_combo.setCurrentIndex(indice if indice >= 0 else 0)
        self.categoria_combo.blockSignals(bloqueado)
        utilizadores = sorted({item.utilizador for item in self._itens if item.utilizador})
        atual_user = self.utilizador_combo.currentText()
        if atual_user in ("", "Todos"):
            atual_user = getattr(app_session.current_user, "username", None) or "Todos"
        bloqueado = self.utilizador_combo.blockSignals(True)
        self.utilizador_combo.clear(); self.utilizador_combo.addItem("Todos")
        self.utilizador_combo.addItems(utilizadores)
        indice = self.utilizador_combo.findText(atual_user)
        self.utilizador_combo.setCurrentIndex(indice if indice >= 0 else 0)
        self.utilizador_combo.blockSignals(bloqueado)
        self._aplicar_filtros()
        self.status.setText("Auditoria concluída; nenhuma alteração foi efetuada.")

    def _preencher_saude(self, resumos) -> None:
        self._resumos_por_linha = {}
        self.saude_table.setRowCount(len(resumos))
        for row, resumo in enumerate(resumos):
            self._resumos_por_linha[row] = resumo
            valores = [resumo.codigo_orcamento, resumo.cliente, resumo.item,
                       f"{resumo.saude_pct}%", str(resumo.criticos), str(resumo.avisos),
                       format_currency(resumo.impacto_conhecido)]
            for col, valor in enumerate(valores):
                cell = QTableWidgetItem(valor)
                if col == 3:
                    cor = "#d4edda" if resumo.saude_pct >= 80 else "#fff3cd" if resumo.saude_pct >= 50 else "#f8d7da"
                    cell.setBackground(QColor(cor))
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.saude_table.setItem(row, col, cell)

    def _abrir_resumo(self, row: int, _column: int) -> None:
        resumo = self._resumos_por_linha.get(row)
        if resumo is not None and self.on_open_orcamento is not None:
            self.on_open_orcamento(resumo)

    def _aplicar_filtros(self, *_args) -> None:
        severidade = self.severidade_combo.currentText()
        categoria = self.categoria_combo.currentText()
        utilizador = self.utilizador_combo.currentText()
        termo = self.pesquisa.text().strip().casefold()
        itens = [item for item in self._itens
                 if (severidade == "Todas" or item.severidade == severidade)
                 and (categoria == "Todas" or item.categoria == categoria)
                 and (utilizador == "Todos" or item.utilizador == utilizador)
                 and (not termo or termo in self._texto(item).casefold())]
        self._preencher(itens)

    @staticmethod
    def _texto(item: CusteioAuditoriaItem) -> str:
        return " ".join((item.codigo_orcamento, item.cliente, item.utilizador,
                         item.item, item.linha,
                         item.problema, item.acao, item.codigo_teste))

    def _preencher(self, itens: list[CusteioAuditoriaItem]) -> None:
        self._por_linha = {}
        self.table.setRowCount(len(itens))
        for row, item in enumerate(itens):
            self._por_linha[row] = item
            valores = [item.severidade, item.categoria, item.codigo_orcamento,
                       item.cliente, item.utilizador, item.item, item.linha, item.problema,
                       item.impacto_texto, item.acao, item.codigo_teste]
            for col, valor in enumerate(valores):
                cell = QTableWidgetItem(valor)
                cell.setToolTip(valor)
                if col == 0:
                    cell.setBackground(QColor("#f8d7da" if item.severidade == CRITICO else "#fff3cd"))
                    cell.setData(Qt.ItemDataRole.UserRole, item.linha_id)
                self.table.setItem(row, col, cell)
        self.table.resizeRowsToContents()
        self._atualizar_abrir()

    def _atualizar_abrir(self) -> None:
        self.abrir_button.setEnabled(self.table.currentRow() >= 0 and self.on_open_orcamento is not None)

    def abrir_orcamento(self) -> None:
        item = self._por_linha.get(self.table.currentRow())
        if item is not None and self.on_open_orcamento is not None:
            self.on_open_orcamento(item)

    def focar_ocorrencia(self, ocorrencia=None) -> bool:
        """Focus the audit row selected by the PDF/email supervisor."""
        self.severidade_combo.setCurrentText("Todas")
        self.categoria_combo.setCurrentText("Todas")
        self.utilizador_combo.setCurrentText("Todos")
        if ocorrencia is None:
            self.pesquisa.clear()
            self._aplicar_filtros()
            self.status.setText(
                "Auditoria aberta pelo supervisor; não existem ocorrências nesta versão."
            )
            return False

        self.pesquisa.setText(ocorrencia.codigo_orcamento)
        self._aplicar_filtros()
        for row, item in self._por_linha.items():
            if (
                item.orcamento_versao_id == ocorrencia.orcamento_versao_id
                and item.orcamento_item_id == ocorrencia.orcamento_item_id
                and item.linha_id == ocorrencia.linha_id
            ):
                self.table.selectRow(row)
                cell = self.table.item(row, 0)
                if cell is not None:
                    self.table.scrollToItem(cell)
                self.status.setText(
                    f"Ocorrência {item.codigo_teste} indicada pelo supervisor."
                )
                return True
        self.status.setText(
            "Auditoria aberta pelo supervisor; a ocorrência já não está ativa."
        )
        return False
