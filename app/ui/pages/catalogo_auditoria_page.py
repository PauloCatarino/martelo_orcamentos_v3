"""Read-only catalog audit results page."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
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
from app.services.catalogo_auditoria_correcao_service import (
    CatalogoAuditoriaCorrecaoService,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class CatalogoAuditoriaPage(QWidget):
    """Display findings and offer only explicit, supervised safe corrections."""

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

    def __init__(
        self,
        on_open_configuracao: Callable[[CatalogoAuditoriaItem], None] | None = None,
    ) -> None:
        super().__init__()
        self.on_open_configuracao = on_open_configuracao
        self._itens: tuple[CatalogoAuditoriaItem, ...] = tuple()
        self._itens_por_linha: dict[int, CatalogoAuditoriaItem] = {}

        self.cabecalho = BarraCabecalho(
            "Auditoria do Catálogo",
            [
                "Análise apenas de leitura das peças, associados, operações, "
                "regras, ValueSets e módulos. A análise nunca altera dados; "
                "algumas ocorrências permitem uma correção separada, explicada "
                "e confirmada pelo utilizador."
            ],
        )

        self.executar_button = QPushButton("Atualizar análise")
        self.executar_button.setToolTip(
            "Voltar a analisar o estado atual do catálogo; não aplica correções."
        )
        self.executar_button.clicked.connect(self.carregar)

        self.abrir_button = QPushButton("Abrir configuração")
        self.abrir_button.setEnabled(False)
        self.abrir_button.clicked.connect(self.abrir_configuracao)

        self.resolver_button = QPushButton("Resolver com supervisão...")
        self.resolver_button.setEnabled(False)
        self.resolver_button.clicked.connect(self.resolver_selecionado)

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
        filtros.addWidget(self.abrir_button)
        filtros.addWidget(self.resolver_button)
        filtros.addWidget(QLabel("Severidade:"))
        filtros.addWidget(self.severidade_combo)
        filtros.addWidget(self.pesquisa_input, stretch=1)

        self.resumo_label = QLabel("Auditoria ainda não executada.")
        self.resumo_label.setObjectName("catalogoAuditoriaResumo")
        self.status_label = QLabel("")
        self.status_label.setObjectName("catalogoAuditoriaStatus")
        self.status_label.setWordWrap(True)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.itemSelectionChanged.connect(self._atualizar_acoes)
        self.table.cellDoubleClicked.connect(
            lambda _row, _column: self.abrir_configuracao()
        )
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
        layout.addWidget(self.status_label)
        layout.addWidget(self.resumo_label)
        layout.addWidget(self.table, stretch=1)
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
        self._itens_por_linha = {}
        self.table.setRowCount(len(itens))
        cores = {
            ERRO: QColor("#f8d7da"),
            AVISO: QColor("#fff3cd"),
            INFORMACAO: QColor("#dbeafe"),
        }
        for row, item in enumerate(itens):
            self._itens_por_linha[row] = item
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
        self._atualizar_acoes()

    def _item_selecionado(self) -> CatalogoAuditoriaItem | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return self._itens_por_linha.get(row)

    def _atualizar_acoes(self) -> None:
        item = self._item_selecionado()
        pode_abrir = bool(
            item is not None
            and item.navegacao_tipo
            and item.navegacao_id is not None
            and self.on_open_configuracao is not None
        )
        pode_resolver = bool(
            item is not None
            and item.correcao_codigo
            and item.correcao_alvo_id is not None
        )
        self.abrir_button.setEnabled(pode_abrir)
        self.resolver_button.setEnabled(pode_resolver)
        if item is not None and not pode_resolver:
            self.resolver_button.setToolTip(
                "Esta ocorrência exige uma decisão humana; abra a configuração."
            )
        else:
            self.resolver_button.setToolTip(
                "Mostrar a correção proposta e pedir confirmação antes de alterar."
            )

    def abrir_configuracao(self) -> None:
        """Navigate to the configuration that originated the selected finding."""
        item = self._item_selecionado()
        if (
            item is None
            or not item.navegacao_tipo
            or item.navegacao_id is None
            or self.on_open_configuracao is None
        ):
            self.status_label.setText(
                "Esta ocorrência ainda não tem abertura direta disponível."
            )
            return
        self.on_open_configuracao(item)

    def resolver_selecionado(self) -> None:
        """Explain and apply one safe correction after explicit confirmation."""
        item = self._item_selecionado()
        if item is None or not item.correcao_codigo:
            self.status_label.setText(
                "Esta ocorrência exige análise manual; use Abrir configuração."
            )
            return

        mensagem = (
            f"Problema:\n{item.problema}\n\n"
            f"Correção proposta:\n{item.correcao_descricao}\n\n"
            "A correção só será aplicada após escolher Sim. Depois será executada "
            "uma nova auditoria. Deseja continuar?"
        )
        resposta = QMessageBox.question(
            self,
            "Confirmar correção supervisionada",
            mensagem,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                resultado = CatalogoAuditoriaCorrecaoService(session).aplicar(item)
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(f"Correção não aplicada: {error}")
            return

        self.carregar()
        self.status_label.setText(
            f"{resultado} A auditoria foi atualizada automaticamente."
        )
