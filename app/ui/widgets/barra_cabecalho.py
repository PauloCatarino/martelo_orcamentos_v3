"""Barra de cabeçalho uniforme das páginas (R2.2)."""

from __future__ import annotations

import html
from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.ui import tema


class BarraCabecalho(QWidget):
    """Cabeçalho uniforme: nome do menu (negrito) + campos de info separados por ' | '."""

    def __init__(
        self, titulo: str, campos: Sequence[str] | None = None, parent=None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("barraCabecalho")
        self.label = QLabel()
        self.label.setObjectName("barraCabecalhoLabel")
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setStyleSheet(
            "#barraCabecalhoLabel {"
            f" background-color: {tema.BEGE_AREIA};"
            f" color: {tema.CASTANHO_ESCURO};"
            " padding: 6px 10px; border-radius: 4px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.definir(titulo, campos)

    def definir(self, titulo: str, campos: Sequence[str] | None = None) -> None:
        """Atualiza o título (negrito) e os campos de info (juntos por ' | ')."""
        partes = [f"<b>{html.escape(titulo)}</b>"]
        partes.extend(html.escape(c) for c in (campos or []) if c and c.strip())
        self.label.setText("&nbsp;&nbsp;|&nbsp;&nbsp;".join(partes))
