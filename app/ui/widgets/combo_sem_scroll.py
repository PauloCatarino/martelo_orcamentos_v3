"""Campos que nunca mudam de valor só porque a roda do rato lhes passou por cima.

Dentro de uma tabela grande — ou de um diálogo com muitos campos que se rola —
o rato passa por cima de dezenas de células enquanto se procura a linha certa.
Um ``QComboBox``/``QSpinBox`` normal apanha essa roda e muda de valor sem
ninguém dar por isso. No custeio, isso trocava o material da peça e mexia no
preço do orçamento em silêncio, que foi o que o Paulo reportou em 2026-09-04.

A regra é a mesma em todos: **a roda só conta depois de o campo estar mesmo a
ser usado** (a lista aberta, no caso dos dropdowns; o foco no campo, nos
restantes). Fora disso o evento é devolvido ao pai, para a tabela ou o diálogo
rolarem como o utilizador espera. As setas, o teclado e a escrita direta
continuam todos a funcionar.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox


class _SemRodaSemFoco:
    """Mixin: a roda só mexe no valor quando o campo tem o foco."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Sem foco pela roda: só clique ou teclado põem o campo em foco.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self.hasFocus():
            super().wheelEvent(event)
            return

        event.ignore()


class ComboSemScroll(QComboBox):
    """Dropdown que só responde à roda com a lista aberta."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Only consume the wheel while the popup is open; otherwise scroll the table."""
        if self.view().isVisible():
            super().wheelEvent(event)
            return

        event.ignore()


class SpinSemScroll(_SemRodaSemFoco, QSpinBox):
    """Campo de número inteiro que só responde à roda quando tem o foco."""


class SpinDuploSemScroll(_SemRodaSemFoco, QDoubleSpinBox):
    """Campo de número decimal que só responde à roda quando tem o foco."""


class DataSemScroll(_SemRodaSemFoco, QDateEdit):
    """Campo de data que só responde à roda quando tem o foco."""
