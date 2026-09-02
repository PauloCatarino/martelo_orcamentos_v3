"""Caixa que mostra as obras que o PHC/Streamlit ja' fechou ou arquivou.

Serve dois caminhos: o aviso diario que aparece sozinho de manha (dias uteis,
das 09h00 em diante) e o botao «Sincronizar PHC» do Ponto Situacao. A diferenca
esta' so' no cabecalho -- quando a caixa aparece sozinha tem de se apresentar,
porque ninguem lhe pediu nada.

O ``Desenho`` e a ``Producao`` nunca chegam aqui: sao estados do utilizador.
Ver ``app/services/producao_phc_sync_service.py``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui import tema
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras

#: Como a caixa se apresenta quando aparece sozinha, de manha.
APRESENTACAO = (
    "Sou o analisador diario dos estados do PHC.\n"
    "Todos os dias uteis, as 09h00, vou ver quais das suas obras e' que ja' "
    "foram finalizadas ou arquivadas.\n"
    "O Desenho e a Producao continuam a ser seus — nunca lhes toco."
)

#: O mesmo, quando foi o utilizador a carregar no botao.
PEDIDO_A_MAO = (
    "Estas obras ja' foram finalizadas ou arquivadas fora do Martelo — no "
    "PHC (encomendas de cliente) ou no Streamlit (cliente final).\n"
    "Marque as que quer atualizar."
)

TODOS_OS_RESPONSAVEIS = "Todos"

_COLUNAS = (
    "",
    "Obra",
    "Nº Enc PHC",
    "Cliente",
    "Ref. cliente",
    "Resp.",
    "Entrega",
    "Mudança de estado",
    "Fonte",
    "O que diz lá fora",
)


def _salta_dois_estados(diff: dict) -> bool:
    """A obra ainda esta' em Desenho e ja' vai arquivada, sem passar pelo meio.

    Acontece quando alguem se esquece de por a obra em Producao: ela e' feita,
    e' entregue e so' no fim e' que o Martelo da' por isso.
    """
    return (
        tema._normalizar_estado(diff.get("estado_martelo")) == "desenho"
        and tema._normalizar_estado(diff.get("estado_sugerido")) == "arquivado"
    )


class ProducaoPhcSyncDialog(QDialog):
    """Lista as mudancas de estado e devolve as que o utilizador aceitou."""

    def __init__(self, diffs, parent=None, *, automatico: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Analisador diário de estados do PHC"
            if automatico
            else "Sincronizar estados"
        )
        self.resize(1040, 620)
        self._diffs = list(diffs)
        self._linhas_visiveis = list(range(len(self._diffs)))

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(self._cabecalho(automatico))
        layout.addWidget(self._resumo())
        layout.addLayout(self._barra_de_filtros())
        layout.addWidget(self._tabela(), 1)
        layout.addWidget(self._rodape())

        # So' agora: encher a tabela dispara ``itemChanged`` linha a linha, e a
        # contagem precisa do rodape ja' construido.
        self.table.itemChanged.connect(self._ao_mudar_visto)
        self._aplicar_filtro()

    # ---- cabecalho ---------------------------------------------------------
    def _cabecalho(self, automatico: bool) -> QWidget:
        caixa = QFrame()
        caixa.setFrameShape(QFrame.Shape.NoFrame)
        caixa.setStyleSheet(
            f"QFrame {{ background-color: {tema.BEGE_AREIA};"
            f" border: 1px solid {tema.CINZA_CASTANHO}; border-radius: 6px; }}"
        )
        linha = QHBoxLayout(caixa)
        linha.setContentsMargins(14, 12, 14, 12)
        linha.setSpacing(12)

        icone = QLabel("\U0001f5c2️")
        fonte_icone = QFont()
        fonte_icone.setPointSize(24)
        icone.setFont(fonte_icone)
        icone.setFixedWidth(38)
        icone.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        icone.setStyleSheet("QLabel { border: none; background: transparent; }")
        linha.addWidget(icone)

        texto = QLabel(APRESENTACAO if automatico else PEDIDO_A_MAO)
        texto.setWordWrap(True)
        texto.setStyleSheet(
            f"QLabel {{ border: none; background: transparent;"
            f" color: {tema.TEXTO_NORMAL}; }}"
        )
        linha.addWidget(texto, 1)
        return caixa

    def _resumo(self) -> QWidget:
        arquivar = sum(
            1
            for d in self._diffs
            if tema._normalizar_estado(d.get("estado_sugerido")) == "arquivado"
        )
        finalizar = len(self._diffs) - arquivar
        saltos = sum(1 for d in self._diffs if _salta_dois_estados(d))

        caixa = QWidget()
        linha = QHBoxLayout(caixa)
        linha.setContentsMargins(0, 0, 0, 0)
        linha.setSpacing(8)
        if arquivar:
            linha.addWidget(
                self._etiqueta(f"Para arquivar: {arquivar}", "arquivado")
            )
        if finalizar:
            linha.addWidget(
                self._etiqueta(f"Para finalizar: {finalizar}", "finalizado")
            )
        if saltos:
            linha.addWidget(
                self._etiqueta(
                    f"Ainda em Desenho: {saltos}",
                    "producao",
                    dica=(
                        "Estas obras saltam dois estados de uma vez: ninguém "
                        "as chegou a pôr em Produção no Martelo."
                    ),
                )
            )
        linha.addStretch(1)
        return caixa

    @staticmethod
    def _etiqueta(texto: str, estado: str, *, dica: str = "") -> QLabel:
        fundo, cor = tema.cor_estado_producao(estado)
        etiqueta = QLabel(texto)
        etiqueta.setStyleSheet(
            f"QLabel {{ background-color: {fundo}; color: {cor};"
            " border-radius: 10px; padding: 4px 12px; font-weight: 600; }"
        )
        if dica:
            etiqueta.setToolTip(dica)
        return etiqueta

    # ---- filtros -----------------------------------------------------------
    def _barra_de_filtros(self) -> QHBoxLayout:
        barra = QHBoxLayout()
        barra.setSpacing(6)

        barra.addWidget(QLabel("Responsável:"))
        self.responsavel_combo = QComboBox()
        self.responsavel_combo.setMinimumWidth(160)
        self.responsavel_combo.setToolTip(
            "Mostrar só as obras de um responsável."
        )
        nomes = sorted(
            {(d.get("responsavel") or "").strip() for d in self._diffs} - {""}
        )
        self.responsavel_combo.addItem(TODOS_OS_RESPONSAVEIS)
        for nome in nomes:
            quantas = sum(
                1 for d in self._diffs if (d.get("responsavel") or "").strip() == nome
            )
            self.responsavel_combo.addItem(f"{nome} ({quantas})", nome)
        self.responsavel_combo.currentIndexChanged.connect(self._aplicar_filtro)
        barra.addWidget(self.responsavel_combo)

        barra.addStretch(1)

        self.selecionar_tudo_button = QPushButton("Marcar todas")
        self.selecionar_tudo_button.setToolTip(
            "Põe o visto em todas as linhas visíveis."
        )
        self.selecionar_tudo_button.clicked.connect(self._selecionar_tudo)
        barra.addWidget(self.selecionar_tudo_button)

        self.desmarcar_tudo_button = QPushButton("Desmarcar todas")
        self.desmarcar_tudo_button.setToolTip(
            "Tira o visto de todas as linhas visíveis."
        )
        self.desmarcar_tudo_button.clicked.connect(self._desmarcar_tudo)
        barra.addWidget(self.desmarcar_tudo_button)
        return barra

    def _aplicar_filtro(self, *_args) -> None:
        escolhido = self.responsavel_combo.currentData()
        for linha, diff in enumerate(self._diffs):
            esconder = bool(escolhido) and (
                (diff.get("responsavel") or "").strip() != escolhido
            )
            self.table.setRowHidden(linha, esconder)
        self._linhas_visiveis = [
            linha for linha in range(len(self._diffs)) if not self.table.isRowHidden(linha)
        ]
        self._atualizar_contagem()

    def escolher_responsavel(self, nome: str) -> bool:
        """Deixar a caixa aberta ja' filtrada por este responsavel."""
        indice = self.responsavel_combo.findData((nome or "").strip())
        if indice < 0:
            return False
        self.responsavel_combo.setCurrentIndex(indice)
        return True

    # ---- tabela ------------------------------------------------------------
    def _tabela(self) -> QTableWidget:
        self.table = QTableWidget(len(self._diffs), len(_COLUNAS))
        self.table.setHorizontalHeaderLabels(list(_COLUNAS))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(tema.ESTILO_VISTAS_DADOS)

        for linha, diff in enumerate(self._diffs):
            self._preencher_linha(linha, diff)

        cabecalho = self.table.horizontalHeader()
        for coluna in range(len(_COLUNAS)):
            cabecalho.setSectionResizeMode(
                coluna,
                QHeaderView.ResizeMode.Stretch
                if coluna == 3
                else QHeaderView.ResizeMode.ResizeToContents,
            )
        ligar_persistencia_larguras(self.table, "dialog_producao_phc_sync")
        return self.table

    def _preencher_linha(self, linha: int, diff: dict) -> None:
        visto = QTableWidgetItem()
        visto.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        # Ja' marcadas: quando o PHC diz que a obra fechou, fechou mesmo.
        visto.setCheckState(Qt.CheckState.Checked)
        self.table.setItem(linha, 0, visto)

        mudanca = (
            f"{diff.get('estado_martelo', '')}  →  "
            f"{diff.get('estado_sugerido', '')}"
        )
        valores = (
            diff.get("codigo", ""),
            diff.get("num_enc_phc", ""),
            diff.get("cliente", ""),
            diff.get("ref_cliente", "") or "—",
            diff.get("responsavel", "") or "—",
            diff.get("data_entrega", "") or "—",
            mudanca,
            diff.get("fonte", "PHC"),
            str(diff.get("estado_phc_raw") or "").strip(),
        )
        for deslocamento, valor in enumerate(valores, start=1):
            item = QTableWidgetItem(str(valor))
            self.table.setItem(linha, deslocamento, item)

        fundo, cor = tema.cor_estado_producao(diff.get("estado_sugerido"))
        item_mudanca = self.table.item(linha, 7)
        if fundo and item_mudanca is not None:
            item_mudanca.setBackground(QColor(fundo))
            item_mudanca.setForeground(QColor(cor))
            fonte = item_mudanca.font()
            fonte.setBold(True)
            item_mudanca.setFont(fonte)

        if _salta_dois_estados(diff):
            item_obra = self.table.item(linha, 1)
            if item_obra is not None:
                item_obra.setToolTip(
                    "Esta obra ainda está em Desenho no Martelo e já vai "
                    "arquivada: salta dois estados de uma vez."
                )
                fonte = item_obra.font()
                fonte.setBold(True)
                item_obra.setFont(fonte)

    def _ao_mudar_visto(self, _item) -> None:
        self._atualizar_contagem()

    # ---- rodape ------------------------------------------------------------
    def _rodape(self) -> QWidget:
        caixa = QWidget()
        linha = QHBoxLayout(caixa)
        linha.setContentsMargins(0, 0, 0, 0)

        self.contagem_label = QLabel()
        self.contagem_label.setStyleSheet(
            f"QLabel {{ color: {tema.CASTANHO_ESCURO}; font-weight: 600; }}"
        )
        linha.addWidget(self.contagem_label)
        linha.addStretch(1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setText("Atualizar as marcadas")
        self._ok_button.setToolTip(
            "Grava o novo estado no Martelo, só nas obras com visto."
        )
        cancelar = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancelar.setText("Ver depois")
        cancelar.setToolTip("Fecha sem alterar nada. Volto a avisar amanhã.")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        linha.addWidget(self.button_box)
        return caixa

    def _atualizar_contagem(self) -> None:
        marcadas = len(self.selecionados())
        visiveis = len(self._linhas_visiveis)
        self.contagem_label.setText(
            f"{marcadas} de {visiveis} obra(s) marcadas para atualizar"
        )
        self._ok_button.setEnabled(marcadas > 0)

    # ---- resultado ---------------------------------------------------------
    def selecionados(self):
        """Pares ``(id, estado)`` das linhas com visto e visíveis."""
        escolhidos = []
        for linha, diff in enumerate(self._diffs):
            if self.table.isRowHidden(linha):
                continue
            visto = self.table.item(linha, 0)
            if visto is not None and visto.checkState() == Qt.CheckState.Checked:
                escolhidos.append((diff["id"], diff["estado_sugerido"]))
        return escolhidos

    def _selecionar_tudo(self) -> None:
        self._marcar_todas(Qt.CheckState.Checked)

    def _desmarcar_tudo(self) -> None:
        self._marcar_todas(Qt.CheckState.Unchecked)

    def _marcar_todas(self, estado: Qt.CheckState) -> None:
        anterior = self.table.blockSignals(True)
        try:
            for linha in self._linhas_visiveis:
                item = self.table.item(linha, 0)
                if item is not None:
                    item.setCheckState(estado)
        finally:
            self.table.blockSignals(anterior)
        self._atualizar_contagem()
