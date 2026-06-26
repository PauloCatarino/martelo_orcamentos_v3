"""Diálogo de progresso do envio para o CUT-RITE."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class CutRiteProgressDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Enviar CUT-RITE")
        self.setModal(False)
        self.resize(680, 420)

        layout = QVBoxLayout(self)
        self._label = QLabel(
            "Passos executados pelo Martelo para criar o plano no CUT-RITE."
        )
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

        self._log = QPlainTextEdit(self)
        self._log.setReadOnly(True)
        layout.addWidget(self._log, 1)

        self._close_button = QPushButton("Fechar", self)
        self._close_button.setEnabled(False)
        self._close_button.clicked.connect(self.accept)
        botoes = QHBoxLayout()
        botoes.addStretch(1)
        botoes.addWidget(self._close_button)
        layout.addLayout(botoes)

    def add_step(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log.appendPlainText(f"[{timestamp}] {message}")

    def finish(self, *, success: bool) -> None:
        self.add_step("Concluído." if success else "Interrompido com erro.")
        self._close_button.setEnabled(True)
