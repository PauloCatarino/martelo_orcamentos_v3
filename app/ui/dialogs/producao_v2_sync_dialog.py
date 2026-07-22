"""Dialog showing V2 -> V3 production differences before importing them."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.producao_v2_sync_service import (
    ComparacaoV2,
    DiferencaV2,
    ObraNovaV2,
)
from app.ui import tema


_COL_APLICAR = 0
_COL_PROCESSO = 1
_COL_CAMPO = 2
_COL_V2 = 3
_COL_V3 = 4


class ProducaoV2SyncDialog(QDialog):
    """Let the user pick which V2 values overwrite V3.

    Nothing is selected by default when V3 already has a value: in the
    transition the V3 data is the one that prevails.
    """

    def __init__(self, comparacao: ComparacaoV2, parent=None) -> None:
        super().__init__(parent)

        self._comparacao = comparacao
        self.obras_novas_escolhidas: list[ObraNovaV2] = []
        self.diferencas_escolhidas: list[DiferencaV2] = []

        self.setWindowTitle("Atualizar dados do V2")
        self.setModal(True)
        self.resize(1100, 620)

        resumo = QLabel(
            f"Obras lidas no V2: {comparacao.total_v2}  ·  "
            f"novas: {len(comparacao.obras_novas)}  ·  "
            f"campos diferentes: {len(comparacao.diferencas)}  ·  "
            f"sem alterações: {comparacao.sem_alteracoes}"
        )
        resumo.setStyleSheet(f"color: {tema.CASTANHO_ESCURO}; font-weight: bold;")

        aviso = QLabel(
            "Por defeito prevalece o V3: só vêm marcadas as obras novas e os campos "
            "que estão vazios no V3. Marque o que quer trazer do V2. "
            "O V2 nunca é alterado."
        )
        aviso.setWordWrap(True)
        aviso.setStyleSheet(f"color: {tema.TEXTO_AVISO};")

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Aplicar", "Processo", "Campo", "Valor no V2", "Valor atual no V3"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self.table.horizontalHeader()
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(_COL_APLICAR, 70)
        self.table.setColumnWidth(_COL_PROCESSO, 230)
        self.table.setColumnWidth(_COL_CAMPO, 150)
        self.table.setColumnWidth(_COL_V2, 300)
        header.setSectionResizeMode(_COL_V3, QHeaderView.ResizeMode.Stretch)

        self._preencher_tabela()

        self.marcar_todos_button = QPushButton("Marcar tudo")
        self.marcar_todos_button.setToolTip("Trazer do V2 todas as linhas listadas")
        self.marcar_todos_button.clicked.connect(lambda: self._marcar_todos(True))

        self.desmarcar_todos_button = QPushButton("Desmarcar tudo")
        self.desmarcar_todos_button.setToolTip("Manter tudo como está no V3")
        self.desmarcar_todos_button.clicked.connect(lambda: self._marcar_todos(False))

        self.aplicar_button = QPushButton("Aplicar selecionados")
        self.aplicar_button.setToolTip("Gravar no V3 apenas as linhas marcadas")
        self.aplicar_button.clicked.connect(self._confirmar)

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.setToolTip("Fechar sem alterar nada")
        self.cancelar_button.clicked.connect(self.reject)

        botoes = QHBoxLayout()
        botoes.addWidget(self.marcar_todos_button)
        botoes.addWidget(self.desmarcar_todos_button)
        botoes.addStretch()
        botoes.addWidget(self.aplicar_button)
        botoes.addWidget(self.cancelar_button)

        layout = QVBoxLayout(self)
        layout.addWidget(resumo)
        layout.addWidget(aviso)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(botoes)

    def _preencher_tabela(self) -> None:
        linhas = len(self._comparacao.obras_novas) + len(self._comparacao.diferencas)
        self.table.setRowCount(linhas)
        self._checkboxes: list[tuple[QCheckBox, object]] = []

        row = 0
        for obra in self._comparacao.obras_novas:
            self._preencher_linha(
                row,
                origem=obra,
                processo=obra.codigo_processo,
                campo="OBRA NOVA",
                valor_v2=obra.descricao or "criar no V3",
                valor_v3="(não existe)",
                marcado=True,
                destaque=True,
            )
            row += 1

        for diferenca in self._comparacao.diferencas:
            self._preencher_linha(
                row,
                origem=diferenca,
                processo=diferenca.codigo_processo,
                campo=diferenca.rotulo,
                valor_v2=diferenca.texto_v2,
                valor_v3=diferenca.texto_v3,
                marcado=diferenca.v3_vazio,
                destaque=False,
            )
            row += 1

    def _preencher_linha(
        self,
        row: int,
        *,
        origem: object,
        processo: str,
        campo: str,
        valor_v2: str,
        valor_v3: str,
        marcado: bool,
        destaque: bool,
    ) -> None:
        checkbox = QCheckBox()
        checkbox.setChecked(marcado)
        checkbox.setToolTip("Marcado = trazer o valor do V2 para o V3")
        self.table.setCellWidget(row, _COL_APLICAR, checkbox)
        self._checkboxes.append((checkbox, origem))

        for coluna, texto in (
            (_COL_PROCESSO, processo),
            (_COL_CAMPO, campo),
            (_COL_V2, valor_v2),
            (_COL_V3, valor_v3),
        ):
            item = QTableWidgetItem(texto)
            item.setToolTip(texto)
            if destaque:
                item.setForeground(QColor(tema.VERDE_ESCURO))
            self.table.setItem(row, coluna, item)

    def _marcar_todos(self, marcado: bool) -> None:
        for checkbox, _origem in self._checkboxes:
            checkbox.setChecked(marcado)

    def _confirmar(self) -> None:
        self.obras_novas_escolhidas = [
            origem
            for checkbox, origem in self._checkboxes
            if checkbox.isChecked() and isinstance(origem, ObraNovaV2)
        ]
        self.diferencas_escolhidas = [
            origem
            for checkbox, origem in self._checkboxes
            if checkbox.isChecked() and isinstance(origem, DiferencaV2)
        ]
        self.accept()
