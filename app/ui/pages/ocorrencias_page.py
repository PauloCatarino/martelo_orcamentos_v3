"""Todas as ocorrências, de todas as obras.

O diálogo da Produção mostra os tickets de uma obra; esta página mostra-os
todos juntos. Serve para as duas coisas que o diálogo não consegue: ver o que
está por resolver em toda a casa, e contar os erros do ano por tipo e por
responsável.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain import ocorrencia_tipos as tipos
from app.services.equipa_service import listar_membros
from app.services.producao_ocorrencias_service import (
    formatar_data,
    listar_todas,
    resumo_por_tipo,
)
from app.ui import tema
from app.ui.dialogs.ocorrencias_obra_dialog import CORES_FAMILIA, OcorrenciasObraDialog
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


COLUNAS = ("Obra", "Cliente", "Nº", "Data", "Tipo", "Assunto", "Resp.", "Estado", "Fotos")


class OcorrenciasPage(QWidget):
    """Global ticket list with filters and a year summary."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._linhas: list[dict] = []

        self.cabecalho = BarraCabecalho("Ocorrências")

        ajuda = QLabel(
            "Tickets de todas as obras. Duplo-clique abre os tickets da obra na "
            "janela da Produção, onde se editam, se juntam fotos e se enviam."
        )
        ajuda.setWordWrap(True)
        ajuda.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        self.pesquisa = CampoPesquisa(
            label="Pesquisar:", placeholder="Pesquisar no assunto ou no texto…"
        )
        self.pesquisa.pesquisa_mudou.connect(lambda _t: self.carregar())
        self.pesquisa.limpar_clicado.connect(self._limpar_filtros)

        self.ano_filtro = QComboBox()
        self.ano_filtro.setToolTip("Ano das obras")
        self.ano_filtro.currentIndexChanged.connect(lambda _i: self.carregar())

        self.tipo_filtro = QComboBox()
        self.tipo_filtro.setToolTip("Filtrar por tipo de ticket")
        self.tipo_filtro.addItem("Tipo: todos", None)
        for tipo in tipos.TIPOS:
            self.tipo_filtro.addItem(tipo.rotulo, tipo.chave)
        self.tipo_filtro.currentIndexChanged.connect(lambda _i: self.carregar())

        self.estado_filtro = QComboBox()
        self.estado_filtro.setToolTip(
            "Filtrar por estado. Por omissão mostra tudo — os resolvidos ficam "
            "à vista, com a cor da coluna Estado a distingui-los."
        )
        self.estado_filtro.addItem("Estado: todos", None)
        self.estado_filtro.addItem("Estado: por resolver", "__abertos__")
        for estado in tipos.ESTADOS:
            self.estado_filtro.addItem(estado.rotulo, estado.chave)
        self.estado_filtro.currentIndexChanged.connect(lambda _i: self.carregar())

        self.responsavel_filtro = QComboBox()
        self.responsavel_filtro.setToolTip("Filtrar por responsável")
        self.responsavel_filtro.currentIndexChanged.connect(lambda _i: self.carregar())

        self.atualizar_button = QPushButton("Atualizar")
        self.atualizar_button.setToolTip("Voltar a ler os tickets da base de dados")
        self.atualizar_button.clicked.connect(self.carregar)

        filtros = QHBoxLayout()
        filtros.addWidget(self.pesquisa)
        filtros.addWidget(self.ano_filtro)
        filtros.addWidget(self.tipo_filtro)
        filtros.addWidget(self.estado_filtro)
        filtros.addWidget(self.responsavel_filtro)
        filtros.addStretch()
        filtros.addWidget(self.atualizar_button)

        self.table = QTableWidget(0, len(COLUNAS))
        self.table.setHorizontalHeaderLabels(list(COLUNAS))
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.itemDoubleClicked.connect(lambda _i: self._abrir_obra())
        cabecalho_tabela = self.table.horizontalHeader()
        cabecalho_tabela.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        cabecalho_tabela.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        for coluna, largura in (
            (0, 230),
            (1, 170),
            (2, 48),
            (3, 120),
            (4, 160),
            (6, 110),
            (7, 100),
            (8, 60),
        ):
            self.table.setColumnWidth(coluna, largura)
        ligar_persistencia_larguras(
            self.table, "ocorrencias_todas", forcar_interativas=False
        )

        self.resumo_label = QLabel("")
        self.resumo_label.setWordWrap(True)
        self.resumo_label.setStyleSheet(f"color: {tema.CASTANHO_ESCURO};")

        self.abrir_button = QPushButton("Abrir tickets da obra")
        self.abrir_button.setToolTip("Abrir a janela dos tickets da obra selecionada")
        self.abrir_button.clicked.connect(self._abrir_obra)

        botoes = QHBoxLayout()
        botoes.addWidget(self.abrir_button)
        botoes.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("ocorrenciasPageStatus")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self.cabecalho)
        layout.addWidget(ajuda)
        layout.addLayout(filtros)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.resumo_label)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self._preencher_filtros()
        self.carregar()

    # ---- filtros ---------------------------------------------------------
    def _preencher_filtros(self) -> None:
        ano_atual = datetime.now().year
        self.ano_filtro.blockSignals(True)
        self.ano_filtro.clear()
        # Todos os filtros abrem em "todos": o que não se vê não se resolve.
        self.ano_filtro.addItem("Ano: todos", None)
        for ano in range(ano_atual, ano_atual - 6, -1):
            self.ano_filtro.addItem(str(ano), ano)
        self.ano_filtro.setCurrentIndex(0)
        self.ano_filtro.blockSignals(False)

        try:
            with SessionLocal() as session:
                nomes = [m.nome for m in listar_membros(session)]
        except SQLAlchemyError:
            nomes = []

        self.responsavel_filtro.blockSignals(True)
        self.responsavel_filtro.clear()
        self.responsavel_filtro.addItem("Responsável: todos", None)
        for nome in nomes:
            self.responsavel_filtro.addItem(nome, nome)
        self.responsavel_filtro.blockSignals(False)

    def _limpar_filtros(self) -> None:
        for combo in (
            self.ano_filtro,
            self.tipo_filtro,
            self.estado_filtro,
            self.responsavel_filtro,
        ):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.carregar()

    # ---- dados -----------------------------------------------------------
    def carregar(self) -> None:
        """Read the tickets that match the filters on screen."""
        ano = self.ano_filtro.currentData()
        estado = self.estado_filtro.currentData()
        try:
            with SessionLocal() as session:
                pares = listar_todas(
                    session,
                    ano=ano,
                    tipo=self.tipo_filtro.currentData(),
                    estado=None if estado == "__abertos__" else estado,
                    apenas_abertos=estado == "__abertos__",
                    responsavel=self.responsavel_filtro.currentData(),
                    texto=self.pesquisa.texto(),
                )
                self._linhas = [
                    {
                        "producao_id": int(obra.id),
                        "codigo": obra.codigo_processo or "",
                        "cliente": obra.nome_cliente or "",
                        "numero": ticket.numero,
                        "created_at": ticket.created_at,
                        "tipo": ticket.tipo,
                        "assunto": ticket.assunto or ticket.texto,
                        "texto": ticket.texto,
                        "responsavel": ticket.responsavel,
                        "estado": ticket.estado,
                        "anexos": len(ticket.anexos or []),
                    }
                    for obra, ticket in pares
                ]
                resumo = resumo_por_tipo(session, ano=ano)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar as ocorrências.")
            return

        self._render(resumo, ano)

    def _render(self, resumo: dict[str, int], ano) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._linhas))
        for indice, linha in enumerate(self._linhas):
            obra = QTableWidgetItem(linha["codigo"])
            obra.setData(Qt.ItemDataRole.UserRole, linha["producao_id"])
            self.table.setItem(indice, 0, obra)
            self.table.setItem(indice, 1, QTableWidgetItem(linha["cliente"]))
            self.table.setItem(
                indice, 2, QTableWidgetItem(tipos.rotulo_ticket(linha["numero"]))
            )
            self.table.setItem(
                indice, 3, QTableWidgetItem(formatar_data(linha["created_at"]))
            )
            self.table.setItem(
                indice,
                4,
                self._badge(
                    tipos.rotulo_tipo(linha["tipo"]), tipos.familia_tipo(linha["tipo"])
                ),
            )
            assunto = QTableWidgetItem(linha["assunto"])
            assunto.setToolTip(linha["texto"])
            self.table.setItem(indice, 5, assunto)
            self.table.setItem(indice, 6, QTableWidgetItem(linha["responsavel"] or "—"))
            self.table.setItem(
                indice,
                7,
                self._badge(
                    tipos.rotulo_estado(linha["estado"]),
                    tipos.familia_estado(linha["estado"]),
                ),
            )
            fotos = QTableWidgetItem(str(linha["anexos"]) if linha["anexos"] else "—")
            fotos.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(indice, 8, fotos)
        self.table.setSortingEnabled(True)

        self.cabecalho.definir(
            "Ocorrências",
            [f"Ano {ano}" if ano else "Todos os anos", f"{len(self._linhas)} ticket(s)"],
        )
        self.resumo_label.setText(self._texto_resumo(resumo))
        abertos = sum(1 for linha in self._linhas if tipos.esta_aberto(linha["estado"]))
        self.status_label.setText(
            f"{len(self._linhas)} ticket(s) na lista, {abertos} por resolver."
            if self._linhas
            else "Sem tickets com estes filtros."
        )

    @staticmethod
    def _texto_resumo(resumo: dict[str, int]) -> str:
        """One line with the year's mistakes, biggest first."""
        if not resumo:
            return ""

        erros = {
            chave: total for chave, total in resumo.items() if tipos.e_erro_nosso(chave)
        }
        total_erros = sum(erros.values())
        maiores = sorted(erros.items(), key=lambda par: par[1], reverse=True)[:4]
        detalhe = ", ".join(
            f"{tipos.rotulo_tipo(chave)}: {total}" for chave, total in maiores
        )
        outros = sum(total for chave, total in resumo.items() if not tipos.e_erro_nosso(chave))
        return (
            f"Erros nossos: {total_erros}"
            + (f" ({detalhe})" if detalhe else "")
            + f"   |   Pedidos e casos externos: {outros}"
        )

    @staticmethod
    def _badge(texto: str, familia: str) -> QTableWidgetItem:
        item = QTableWidgetItem(texto)
        fundo, cor = CORES_FAMILIA.get(familia, CORES_FAMILIA["neutro"])
        item.setBackground(QColor(fundo))
        item.setForeground(QColor(cor))
        return item

    # ---- ações -----------------------------------------------------------
    def _abrir_obra(self) -> None:
        indice = self.table.currentRow()
        if indice < 0:
            self.status_label.setText("Selecione um ticket para abrir a obra.")
            return

        item = self.table.item(indice, 0)
        if item is None:
            return
        producao_id = item.data(Qt.ItemDataRole.UserRole)
        if producao_id is None:
            return

        dialog = OcorrenciasObraDialog(
            producao_id=int(producao_id),
            codigo_processo=item.text(),
            parent=self,
        )
        dialog.exec()
        self.carregar()
