"""Line edit that shows a measurement unit inside the field (right side).

Reusable across the app wherever a numeric value carries a fixed unit (€, %,
€/m², ...): the unit is painted inside the cell, to the right of the value, so
the user always knows what the number means — whether it came pre-filled from
the raw materials or is typed manually. It subclasses ``QLineEdit`` so every
existing ``.text()`` / ``.setText()`` call keeps working unchanged.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit


class CampoValorComUnidade(QLineEdit):
    """Editable value field with the measurement unit shown inside the field."""

    _MARGEM_UNIDADE = 8

    def __init__(self, unidade: str = "", parent=None) -> None:
        super().__init__(parent)
        self._unidade = ""
        self._unidade_label = QLabel("", self)
        self._unidade_label.setObjectName("campoValorUnidade")
        # The unit is decoration only: never steal focus/clicks from the field.
        self._unidade_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._unidade_label.setStyleSheet(
            "QLabel#campoValorUnidade { color: #6b6b6b; background: transparent; }"
        )
        self.definir_unidade(unidade)

    def definir_unidade(self, unidade: str) -> None:
        """Set (or clear) the unit shown at the right of the field."""
        self._unidade = unidade or ""
        self._unidade_label.setText(self._unidade)
        self._unidade_label.adjustSize()
        margem_direita = (
            self._unidade_label.width() + 2 * self._MARGEM_UNIDADE
            if self._unidade
            else 0
        )
        self.setTextMargins(0, 0, margem_direita, 0)
        self._unidade_label.setVisible(bool(self._unidade))
        self._reposicionar_unidade()

    def marcar_como_resultado(self, tooltip: str | None = None) -> None:
        """Turn the field into a protected, highlighted computed-result field.

        Read-only, bold and slightly larger, with an optional tooltip carrying
        the formula. Used for values the user must not edit (e.g. liquid price).
        """
        self.setReadOnly(True)
        fonte = self.font()
        fonte.setBold(True)
        fonte.setPointSizeF(fonte.pointSizeF() + 1)
        self.setFont(fonte)
        self.setStyleSheet(
            "QLineEdit { background: #f0efe9; font-weight: bold; }"
        )
        if tooltip:
            self.setToolTip(tooltip)
        # Font/size changed: recompute the unit position and margin.
        self.definir_unidade(self._unidade)

    def _reposicionar_unidade(self) -> None:
        if not self._unidade:
            return
        rect = self.rect()
        x = rect.right() - self._unidade_label.width() - self._MARGEM_UNIDADE
        y = (rect.height() - self._unidade_label.height()) // 2
        self._unidade_label.move(max(x, 0), max(y, 0))

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._reposicionar_unidade()
