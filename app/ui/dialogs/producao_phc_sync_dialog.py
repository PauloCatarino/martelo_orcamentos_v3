"""Dialog for validating Producao <- PHC state sync by checkbox."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class ProducaoPhcSyncDialog(QDialog):
    def __init__(self, diffs, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sincronizar estados")
        self.resize(900, 520)
        self._diffs = diffs

        layout = QVBoxLayout(self)
        info = QLabel(
            "O PHC/Streamlit sugere estados diferentes para estas obras. "
            "Marque as que quer atualizar no Martelo."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget(len(diffs), 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Atualizar",
                "Processo",
                "N\u00ba Enc PHC",
                "Fonte",
                "Cliente",
                "Estado Martelo",
                "Estado sugerido",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        for row_index, diff in enumerate(diffs):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(row_index, 0, chk)
            self.table.setItem(row_index, 1, QTableWidgetItem(diff["codigo"]))
            self.table.setItem(
                row_index,
                2,
                QTableWidgetItem(diff.get("num_enc_phc", "")),
            )
            self.table.setItem(row_index, 3, QTableWidgetItem(diff.get("fonte", "PHC")))
            self.table.setItem(row_index, 4, QTableWidgetItem(diff["cliente"]))
            self.table.setItem(row_index, 5, QTableWidgetItem(diff["estado_martelo"]))
            raw = str(diff.get("estado_phc_raw") or "").strip()
            sugerido = diff["estado_sugerido"] + (f"  ({raw})" if raw else "")
            self.table.setItem(
                row_index,
                6,
                QTableWidgetItem(sugerido),
            )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
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
                out.append((diff["id"], diff["estado_sugerido"]))
        return out
