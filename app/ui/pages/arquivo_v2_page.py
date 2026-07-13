"""Read-only Martelo V2 budget archive page."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.services.v2_arquivo_service import (
    V2ArquivoConfigError, V2ArquivoSchemaError, V2ArquivoService,
    criar_engine_v2_readonly,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.estilo_tabela_orcamentos import configurar_tabela_orcamentos
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency


class ArquivoV2Page(QWidget):
    HEADERS = ["Orçamento", "Versão", "Estado", "Cliente", "Ref. Cliente", "Obra",
               "Descrição", "Data", "Total", "Utilizador", "Origem"]

    def __init__(self) -> None:
        super().__init__()
        self._todos = []
        self.cabecalho = BarraCabecalho(
            "Arquivo de Orçamentos V2",
            ["Consulta direta e apenas de leitura. Os dados V2 não são importados nem editados."],
        )
        self.atualizar = QPushButton("Ligar / Atualizar")
        self.atualizar.setToolTip("Tentar ligar à base V2 e reler o arquivo sem efetuar escritas")
        self.atualizar.clicked.connect(self.carregar)
        self.pesquisa = CampoPesquisa(
            placeholder="Pesquisar número, cliente, referência, obra ou descrição…"
        )
        self.pesquisa.pesquisa_mudou.connect(self._render)
        self.pesquisa.limpar_clicado.connect(self._render)
        self.estado = QComboBox(); self.estado.addItem("Todos")
        self.estado.currentTextChanged.connect(self._render)
        filtros = QHBoxLayout()
        filtros.addWidget(self.atualizar)
        filtros.addWidget(self.pesquisa, stretch=1)
        filtros.addWidget(QLabel("Estado")); filtros.addWidget(self.estado)
        self.status = QLabel("Arquivo V2 ainda não consultado.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("padding: 7px; font-weight: bold;")
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        configurar_tabela_orcamentos(self.table, compacta=True)
        ligar_persistencia_larguras(self.table, "arquivo_orcamentos_v2")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(self.cabecalho); layout.addLayout(filtros)
        layout.addWidget(self.status); layout.addWidget(self.table, stretch=1)

    def carregar(self) -> None:
        self.atualizar.setEnabled(False)
        self.status.setText("A ligar ao Arquivo V2 em modo apenas de leitura…")
        engine = None
        try:
            engine = criar_engine_v2_readonly()
            self._todos = V2ArquivoService(engine).listar_orcamentos()
        except (V2ArquivoConfigError, V2ArquivoSchemaError) as error:
            self._todos = []
            self.status.setText(str(error))
            self._render()
            return
        except SQLAlchemyError:
            self._todos = []
            self.status.setText(
                "Não foi possível consultar a base V2. Confirme rede, servidor e credenciais read-only."
            )
            self._render()
            return
        finally:
            if engine is not None:
                engine.dispose()
            self.atualizar.setEnabled(True)
        self._popular_estados()
        self._render()
        tabela = self._todos[0].tabela_origem if self._todos else "—"
        self.status.setText(
            f"Arquivo V2 ligado · {len(self._todos)} registos · tabela {tabela} · apenas leitura"
        )

    def _popular_estados(self) -> None:
        atual = self.estado.currentText()
        bloqueado = self.estado.blockSignals(True)
        self.estado.clear(); self.estado.addItem("Todos")
        self.estado.addItems(sorted({item.estado for item in self._todos if item.estado}))
        indice = self.estado.findText(atual)
        self.estado.setCurrentIndex(indice if indice >= 0 else 0)
        self.estado.blockSignals(bloqueado)

    def _render(self, *_args) -> None:
        termos = [t.casefold() for t in self.pesquisa.texto().split() if t]
        estado = self.estado.currentText()
        filtrados = []
        for item in self._todos:
            texto = " ".join((item.numero, item.versao, item.cliente, item.ref_cliente,
                              item.obra, item.descricao, item.estado, item.utilizador)).casefold()
            if termos and not all(t in texto for t in termos):
                continue
            if estado not in ("", "Todos") and item.estado != estado:
                continue
            filtrados.append(item)
        self.table.setRowCount(len(filtrados))
        for row, item in enumerate(filtrados):
            data = item.data.strftime("%d/%m/%Y") if hasattr(item.data, "strftime") else str(item.data or "")
            valores = [item.numero, item.versao, item.estado, item.cliente, item.ref_cliente,
                       item.obra, item.descricao, data, format_currency(item.total),
                       item.utilizador, f"V2 · {item.tabela_origem}"]
            for col, valor in enumerate(valores):
                cell = QTableWidgetItem(valor); cell.setToolTip(valor)
                self.table.setItem(row, col, cell)
