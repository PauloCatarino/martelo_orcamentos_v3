"""QComboBox that ignores the mouse wheel until it is deliberately opened."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox


class ComboSemScroll(QComboBox):
    """A combobox inside a table that never changes value on a stray scroll.

    Dentro de uma tabela grande, o rato passa por cima de dezenas de células
    enquanto se rola a lista. Um QComboBox normal apanha essa roda e muda de
    opção sem ninguém dar por isso — no custeio, isso trocava o material da peça
    e mudava o preço do orçamento em silêncio.

    Aqui a roda só mexe na lista quando ela está mesmo aberta (o utilizador
    carregou na seta). Fora disso, o evento é devolvido ao pai, para a tabela
    rolar como o utilizador espera.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # Sem foco pela roda: só clique ou teclado põem a caixa em foco.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Only consume the wheel while the popup is open; otherwise scroll the table."""
        if self.view().isVisible():
            super().wheelEvent(event)
            return

        event.ignore()
