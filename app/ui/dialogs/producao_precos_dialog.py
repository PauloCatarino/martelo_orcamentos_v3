"""Price validation dialog: Martelo vs PHC/Streamlit, with row checkboxes."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class ProducaoPrecosDialog(QDialog):
    def __init__(self, diffs, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Validar pre\u00e7os de venda")
        self.resize(960, 540)
        self._diffs = diffs

        layout = QVBoxLayout(self)
        info = QLabel(
            "Pre\u00e7o do Martelo vs pre\u00e7o de venda no PHC/Streamlit. "
            "Obras SEM pre\u00e7o j\u00e1 v\u00eam marcadas; para sobrescrever um "
            "pre\u00e7o existente, marque a linha."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        bulk_layout = QHBoxLayout()
        btn_selecionar_tudo = QPushButton("Selecionar tudo")
        btn_desmarcar_tudo = QPushButton("Desmarcar tudo")
        btn_selecionar_tudo.clicked.connect(self._selecionar_tudo)
        btn_desmarcar_tudo.clicked.connect(self._desmarcar_tudo)
        bulk_layout.addWidget(btn_selecionar_tudo)
        bulk_layout.addWidget(btn_desmarcar_tudo)
        bulk_layout.addStretch(1)
        layout.addLayout(bulk_layout)

        self.table = QTableWidget(len(diffs), 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Atualizar",
                "Processo",
                "N\u00ba Enc",
                "Fonte",
                "Cliente",
                "Pre\u00e7o Martelo",
                "Pre\u00e7o externo",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        for row_index, diff in enumerate(diffs):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(
                Qt.CheckState.Checked
                if diff["default_check"]
                else Qt.CheckState.Unchecked
            )
            self.table.setItem(row_index, 0, chk)
            self.table.setItem(row_index, 1, QTableWidgetItem(diff["codigo"]))
            self.table.setItem(row_index, 2, QTableWidgetItem(diff["num_enc"]))
            self.table.setItem(row_index, 3, QTableWidgetItem(diff["fonte"]))
            self.table.setItem(row_index, 4, QTableWidgetItem(diff["cliente"]))

            martelo = (
                "-"
                if diff["preco_martelo"] is None
                else f"{diff['preco_martelo']:.2f} \u20ac"
            )
            self.table.setItem(row_index, 5, QTableWidgetItem(martelo))
            self.table.setItem(
                row_index,
                6,
                QTableWidgetItem(f"{diff['preco_externo']:.2f} \u20ac"),
            )

        header = self.table.horizontalHeader()
        for col in (0, 1, 2, 3, 5, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        ligar_persistencia_larguras(self.table, "dialog_producao_precos")
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Atualizar selecionados"
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selecionados(self):
        out = []
        for row_index, diff in enumerate(self._diffs):
            chk = self.table.item(row_index, 0)
            if chk is not None and chk.checkState() == Qt.CheckState.Checked:
                out.append((diff["id"], diff["preco_externo"]))
        return out

    def _selecionar_tudo(self) -> None:
        self._marcar_todas(Qt.CheckState.Checked)

    def _desmarcar_tudo(self) -> None:
        self._marcar_todas(Qt.CheckState.Unchecked)

    def _marcar_todas(self, estado: Qt.CheckState) -> None:
        estado_anterior = self.table.blockSignals(True)
        try:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item is not None:
                    item.setCheckState(estado)
        finally:
            self.table.blockSignals(estado_anterior)
