"""Dialog for choosing visible production table columns."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.helpers.colunas_producao import ColunaProducao


class ColunasProducaoDialog(QDialog):
    """Modal dialog to select visible columns in the production list."""

    def __init__(
        self,
        parent,
        colunas: list[ColunaProducao],
        visiveis: list[str],
    ) -> None:
        super().__init__(parent)

        self.selected_keys: list[str] | None = None
        self._checkboxes: dict[str, QCheckBox] = {}

        self.setWindowTitle("Colunas")
        self.setModal(True)
        self.setMinimumWidth(360)

        visible_set = set(visiveis)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)

        for coluna in colunas:
            checkbox = QCheckBox(coluna.titulo)
            checkbox.setChecked(coluna.key in visible_set)
            self._checkboxes[coluna.key] = checkbox
            content_layout.addWidget(checkbox)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        self.status_label = QLabel("")

        self.ok_button = QPushButton("OK")
        self.ok_button.setToolTip("Aplicar as colunas escolhidas")
        self.ok_button.clicked.connect(self._confirmar)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setToolTip("Fechar sem alterar as colunas")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addWidget(scroll, stretch=1)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def _confirmar(self) -> None:
        selected = [
            key for key, checkbox in self._checkboxes.items() if checkbox.isChecked()
        ]
        if not selected:
            self.status_label.setText("Escolha pelo menos uma coluna.")
            return

        self.selected_keys = selected
        self.accept()
