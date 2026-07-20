"""Reusable search bar widgets."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QToolButton, QWidget

from app.ui.icones import icone_ficheiro


class CampoPesquisa(QWidget):
    """Search field with a brush clear button, reusable across pages."""

    pesquisa_mudou = Signal(str)  # a cada tecla (textChanged)
    pesquisar = Signal(str)       # só ao premir Enter (returnPressed)
    limpar_clicado = Signal()

    def __init__(
        self,
        parent=None,
        *,
        label: str = "Pesquisar:",
        placeholder: str = "Pesquisar \u2014 espa\u00e7o ou % para v\u00e1rios termos\u2026",
        largura_max: int = 360,
    ) -> None:
        super().__init__(parent)

        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setClearButtonEnabled(True)
        self._input.setMaximumWidth(largura_max)
        self._input.textChanged.connect(self.pesquisa_mudou.emit)
        self._input.returnPressed.connect(
            lambda: self.pesquisar.emit(self._input.text())
        )

        self._botao = QToolButton()
        self._botao.setIcon(icone_ficheiro("icon_cleaner.ico"))
        self._botao.setToolTip("Limpar pesquisa e filtros")
        self._botao.setAutoRaise(True)
        self._botao.clicked.connect(self._on_limpar)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        if label:
            layout.addWidget(QLabel(label))
        layout.addWidget(self._input)
        layout.addWidget(self._botao)
        layout.addStretch()

    def texto(self) -> str:
        """Return the current search text."""
        return self._input.text()

    def definir_texto(self, texto: str) -> None:
        """Set the search text (emits pesquisa_mudou, filtering the list)."""
        self._input.setText(texto or "")

    def limpar(self) -> None:
        """Clear the text without emitting limpar_clicado."""
        self._input.clear()

    def _on_limpar(self) -> None:
        self._input.clear()
        self.limpar_clicado.emit()
