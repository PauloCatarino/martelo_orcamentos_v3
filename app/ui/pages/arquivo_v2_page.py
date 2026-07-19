"""Shared Martelo V2 budget archive page."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.v2_arquivo_service import (
    OrcamentoV2Resumo,
    V2ArquivoConfigError,
    V2ArquivoSchemaError,
    V2ArquivoService,
    V2ArquivoWriteError,
    criar_engine_v2,
    criar_engine_v2_readonly,
)
from app.services.v2_arquivo_pastas_service import resolver_pasta_orcamento_v2
from app.ui.dialogs.editar_arquivo_v2_dialog import EditarArquivoV2Dialog
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.estilo_tabela_orcamentos import (
    aplicar_estilo_linha_orcamento,
    configurar_tabela_orcamentos,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency


class ArquivoV2Page(QWidget):
    """List and safely edit the shared V2 budget headers."""

    HEADERS = [
        "Orçamento",
        "Versão",
        "Estado",
        "Enc PHC",
        "Cliente",
        "Ref. Cliente",
        "Obra",
        "Descrição",
        "Data",
        "Total",
        "Origem preço",
        "Utilizador",
        "Origem",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._todos: list[OrcamentoV2Resumo] = []
        self._visiveis: list[OrcamentoV2Resumo] = []

        self.cabecalho = BarraCabecalho(
            "Arquivo de Orçamentos V2",
            [
                "Lista partilhada V2/V3. Estado, Enc PHC e preços manuais podem "
                "ser atualizados aqui; preços de custeio ficam protegidos."
            ],
        )

        self.atualizar = QPushButton("Ligar / Atualizar")
        self.atualizar.setToolTip("Reler a tabela partilhada de orçamentos V2")
        self.atualizar.clicked.connect(self.carregar)

        self.editar = QPushButton("Editar selecionado")
        self.editar.setToolTip("Editar estado, Enc PHC e, quando permitido, preço manual")
        self.editar.clicked.connect(self.editar_selecionado)

        self.abrir_pasta = QPushButton("Abrir pasta")
        self.abrir_pasta.setToolTip("Abrir a pasta existente do orçamento V2 selecionado")
        self.abrir_pasta.clicked.connect(self._abrir_pasta_selecionada)

        self.pesquisa = CampoPesquisa(
            placeholder="Pesquisar número, cliente, referência, obra ou descrição…"
        )
        self.pesquisa.pesquisa_mudou.connect(self._render)
        self.pesquisa.limpar_clicado.connect(self._render)

        self.estado = QComboBox()
        self.estado.addItem("Todos")
        self.estado.currentTextChanged.connect(self._render)

        filtros = QHBoxLayout()
        filtros.addWidget(self.pesquisa)
        filtros.addWidget(self.atualizar)
        filtros.addWidget(self.editar)
        filtros.addWidget(self.abrir_pasta)
        filtros.addWidget(QLabel("Estado"))
        filtros.addWidget(self.estado)
        filtros.addStretch()

        self.status = QLabel("Arquivo V2 ainda não consultado.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("padding: 7px; font-weight: bold;")

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        configurar_tabela_orcamentos(self.table, compacta=True)
        ligar_persistencia_larguras(self.table, "arquivo_orcamentos_v2")
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.editar_selecionado())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(self.cabecalho)
        layout.addLayout(filtros)
        layout.addWidget(self.status)
        layout.addWidget(self.table, stretch=1)

    def carregar(self) -> None:
        """Read the current V2 data using the read-only connection."""
        self.atualizar.setEnabled(False)
        self.status.setText("A ligar ao Arquivo V2…")
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
                "Não foi possível consultar a base V2. Confirme rede, servidor e credenciais."
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
            f"Arquivo V2 ligado · {len(self._todos)} registos · tabela {tabela} · "
            "edição partilhada ativa"
        )

    def _popular_estados(self) -> None:
        atual = self.estado.currentText()
        bloqueado = self.estado.blockSignals(True)
        self.estado.clear()
        self.estado.addItem("Todos")
        self.estado.addItems(sorted({item.estado for item in self._todos if item.estado}))
        indice = self.estado.findText(atual)
        self.estado.setCurrentIndex(indice if indice >= 0 else 0)
        self.estado.blockSignals(bloqueado)

    def _render(self, *_args) -> None:
        termos = [termo.casefold() for termo in self.pesquisa.texto().split() if termo]
        estado = self.estado.currentText()
        self._visiveis = []
        for item in self._todos:
            texto = " ".join(
                (
                    item.numero,
                    item.versao,
                    item.estado,
                    item.enc_phc,
                    item.cliente,
                    item.ref_cliente,
                    item.obra,
                    item.descricao,
                    item.utilizador,
                )
            ).casefold()
            if termos and not all(termo in texto for termo in termos):
                continue
            if estado not in ("", "Todos") and item.estado != estado:
                continue
            self._visiveis.append(item)

        self.table.setRowCount(len(self._visiveis))
        for row, item in enumerate(self._visiveis):
            data = (
                item.data.strftime("%d/%m/%Y")
                if hasattr(item.data, "strftime")
                else str(item.data or "")
            )
            origem = {
                "manual": "Manual",
                "custeio": "Custeio",
                "desconhecida": "Desconhecida",
            }.get(item.origem_preco, item.origem_preco)
            valores = [
                item.numero,
                item.versao,
                item.estado,
                item.enc_phc,
                item.cliente,
                item.ref_cliente,
                item.obra,
                item.descricao,
                data,
                format_currency(item.total),
                origem,
                item.utilizador,
                f"V2 · {item.tabela_origem}",
            ]
            for column, valor in enumerate(valores):
                cell = QTableWidgetItem(str(valor or ""))
                cell.setToolTip(str(valor or ""))
                self.table.setItem(row, column, cell)
            total_index = self.HEADERS.index("Total")
            aplicar_estilo_linha_orcamento(
                self.table,
                row,
                coluna_codigo=0,
                coluna_estado=2,
                estado=item.estado,
                coluna_total=total_index,
                preco_manual=item.preco_editavel,
            )

    def editar_selecionado(self) -> None:
        """Open the controlled editor for the selected V2 row."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visiveis):
            self.status.setText("Selecione um orçamento V2 para editar.")
            return

        item = self._visiveis[row]
        dialog = EditarArquivoV2Dialog(
            item,
            self,
            on_open_folder=lambda: self._abrir_pasta_item(item),
        )
        if not dialog.exec():
            return
        dados = dialog.get_data()

        engine = None
        try:
            engine = criar_engine_v2(read_only=False)
            V2ArquivoService(engine).atualizar_orcamento(
                item,
                estado=dados.estado,
                enc_phc=dados.enc_phc,
                total=dados.total,
            )
        except (V2ArquivoConfigError, V2ArquivoSchemaError, V2ArquivoWriteError, ValueError) as error:
            self.status.setText(str(error))
            return
        except SQLAlchemyError:
            self.status.setText("Não foi possível gravar a alteração na base V2.")
            return
        finally:
            if engine is not None:
                engine.dispose()

        self.status.setText(
            "Orçamento atualizado na base partilhada. O V2 já pode consultar os mesmos dados."
        )
        self.carregar()

    def _abrir_pasta_selecionada(self) -> None:
        """Open the selected legacy folder using the read-only V2 convention."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visiveis):
            self.status.setText("Selecione um orçamento V2 para abrir a pasta.")
            return
        self._abrir_pasta_item(self._visiveis[row])

    def _abrir_pasta_item(self, item: OrcamentoV2Resumo) -> None:
        try:
            with SessionLocal() as session:
                pasta = resolver_pasta_orcamento_v2(session, item)
        except SQLAlchemyError:
            self.status.setText("Não foi possível localizar a pasta do orçamento V2.")
            return

        if pasta is None:
            QMessageBox.information(
                self,
                "Abrir pasta",
                "Não foi encontrada uma pasta existente para este orçamento V2. "
                "Confirme a Pasta base dos Orçamentos em Configurações → Caminhos.",
            )
            return

        self.status.setText(f"Pasta aberta: {pasta}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta)))
