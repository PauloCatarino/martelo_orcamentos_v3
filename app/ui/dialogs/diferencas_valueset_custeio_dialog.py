"""Dialog listing every ValueSet/costing material difference of one item."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.utils.formatters import format_currency
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


#: Teto por coluna ao abrir; o utilizador pode alargar à mão e fica guardado.
_LARGURA_MAXIMA_COLUNA = 260


class DiferencasValuesetCusteioDialog(QDialog):
    """Review, in one table, every cost line whose material lags the ValueSet.

    Substitui o percurso antigo — abrir o ValueSet, escolher uma chave, carregar
    em "Atualizar Custeio", repetir — que era o que fazia falta quando alguém
    troca dez materiais de uma vez.
    """

    TABLE_HEADERS = [
        "Atualizar?",
        "Peça",
        "Descrição",
        "Chave ValueSet",
        "Opção",
        "Ref LE no custeio",
        "Ref LE no ValueSet",
        "Material no custeio",
        "Material no ValueSet",
        "Pliq custeio",
        "Pliq ValueSet",
        "Escolha manual",
        "O que muda",
    ]

    def __init__(self, divergencias: list, parent=None) -> None:
        super().__init__(parent)

        self.divergencias = list(divergencias)
        self.selecionadas: list[tuple[int, int]] = []
        self._por_linha: dict[int, object] = {}

        self.setWindowTitle("Diferenças entre o ValueSet e o Custeio")
        self.setModal(True)
        self.setMinimumSize(1100, 500)
        self._dimensionar_ao_ecra()

        sugeridas = sum(1 for divergencia in self.divergencias if divergencia.sugerido)
        manuais = len(self.divergencias) - sugeridas
        texto = (
            f"{len(self.divergencias)} linha(s) de custeio têm um material diferente "
            "do que está no ValueSet do item. As que vêm marcadas são as que "
            "seguem o ValueSet."
        )
        if manuais:
            texto += (
                f" As outras {manuais} têm material escolhido à mão nessa linha e "
                "vêm desmarcadas — marque-as só se quiser mesmo perder essa escolha."
            )
        info = QLabel(texto)
        info.setWordWrap(True)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        ligar_persistencia_larguras(self.table, "dialog_diferencas_valueset_custeio")

        self.marcar_button = QPushButton("Marcar todas")
        self.marcar_button.setToolTip("Marca todas as linhas da lista, inclusive as de escolha manual.")
        self.marcar_button.clicked.connect(lambda: self._definir_marcacao(True))
        self.desmarcar_button = QPushButton("Desmarcar todas")
        self.desmarcar_button.setToolTip("Desmarca todas as linhas da lista.")
        self.desmarcar_button.clicked.connect(lambda: self._definir_marcacao(False))
        self.update_button = QPushButton("Atualizar selecionadas")
        self.update_button.setToolTip(
            "Copia o material do ValueSet para as linhas marcadas e recalcula os custos."
        )
        self.update_button.clicked.connect(self._atualizar_selecionadas)
        self.cancel_button = QPushButton("Agora não")
        self.cancel_button.setToolTip("Fecha sem mexer no custeio.")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.marcar_button)
        buttons_layout.addWidget(self.desmarcar_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.update_button)
        buttons_layout.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._preencher()

    def _dimensionar_ao_ecra(self) -> None:
        """Abrir o mais largo possível: são treze colunas lado a lado.

        Vale a pena tapar a biblioteca de peças que está por baixo — quem está
        a comparar materiais quer ver as colunas todas de uma vez.
        """
        ecra = QGuiApplication.primaryScreen()
        if ecra is None:
            self.resize(1600, 700)
            return

        disponivel = ecra.availableGeometry()
        largura = min(int(disponivel.width() * 0.96), 2400)
        altura = min(int(disponivel.height() * 0.80), 1000)
        self.resize(max(largura, 1100), max(altura, 500))

    def _preencher(self) -> None:
        """Fill one row per divergence, current value against ValueSet value."""
        self.table.setRowCount(len(self.divergencias))

        for row_index, divergencia in enumerate(self.divergencias):
            linha = divergencia.linha
            vs = divergencia.valueset_linha
            self._por_linha[row_index] = divergencia

            check_item = QTableWidgetItem()
            check_item.setFlags(check_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            check_item.setCheckState(
                Qt.CheckState.Checked
                if divergencia.sugerido
                else Qt.CheckState.Unchecked
            )
            self.table.setItem(row_index, 0, check_item)

            valores = [
                linha.def_peca_codigo or linha.codigo or "",
                linha.descricao or "",
                linha.chave_valueset or "",
                vs.codigo_opcao or vs.nome_opcao or "",
                linha.ref_le or "",
                vs.ref_le or "",
                linha.descricao_no_orcamento or linha.descricao_materia_prima or "",
                vs.descricao_no_orcamento or vs.descricao_materia_prima or "",
                format_currency(linha.preco_liquido) or "",
                format_currency(vs.preco_liquido) or "",
                "Sim" if linha.material_editado_localmente else "Não",
                ", ".join(divergencia.campos),
            ]
            for offset, value in enumerate(valores):
                self.table.setItem(row_index, offset + 1, QTableWidgetItem(value))

        self.table.resizeColumnsToContents()
        # Sem teto, a "Descrição" e os dois materiais comem a largura toda e
        # empurram as Ref LE — que são a coluna que interessa — para fora.
        for coluna in range(self.table.columnCount()):
            if self.table.columnWidth(coluna) > _LARGURA_MAXIMA_COLUNA:
                self.table.setColumnWidth(coluna, _LARGURA_MAXIMA_COLUNA)

    def _definir_marcacao(self, marcar: bool) -> None:
        """Check or uncheck every row at once."""
        estado = Qt.CheckState.Checked if marcar else Qt.CheckState.Unchecked
        for row_index in range(self.table.rowCount()):
            item = self.table.item(row_index, 0)
            if item is not None:
                item.setCheckState(estado)

    def _atualizar_selecionadas(self) -> None:
        """Collect the checked (cost line, ValueSet line) pairs and accept."""
        pares: list[tuple[int, int]] = []
        for row_index, divergencia in self._por_linha.items():
            item = self.table.item(row_index, 0)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                pares.append((divergencia.linha_id, divergencia.valueset_linha_id))

        self.selecionadas = pares
        self.accept()
