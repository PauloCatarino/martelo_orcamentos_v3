"""Reusable search bar widgets."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class CampoPesquisa(QWidget):
    """Search field, reusable across pages.

    Tinha ao lado um botão "pincel" para limpar. Foi retirado: o próprio campo
    já traz um ``X`` lá dentro e dois botões a fazer a mesma coisa só ocupavam
    espaço e confundiam. O espaço que sobrou foi para o campo, que passou a ser
    mais largo.

    Onde o pincel também servia para repor os OUTROS filtros da página (estado,
    cliente, responsável…), essa ação passou a ter um botão próprio, com nome,
    junto desses filtros — ver :class:`BotaoLimparFiltros`.
    """

    pesquisa_mudou = Signal(str)  # a cada tecla (textChanged)
    pesquisar = Signal(str)       # só ao premir Enter (returnPressed)

    def __init__(
        self,
        parent=None,
        *,
        label: str = "Pesquisar:",
        placeholder: str = "Pesquisar — espaço ou % para vários termos…",
        largura_max: int = 420,
    ) -> None:
        super().__init__(parent)

        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setClearButtonEnabled(True)
        self._input.setMaximumWidth(largura_max)
        self._input.setToolTip(
            "Pesquisa em todos os campos. Vários termos: separe por espaço "
            "ou %. O X limpa a pesquisa."
        )
        self._input.textChanged.connect(self.pesquisa_mudou.emit)
        self._input.returnPressed.connect(
            lambda: self.pesquisar.emit(self._input.text())
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        if label:
            layout.addWidget(QLabel(label))
        layout.addWidget(self._input)
        layout.addStretch()

    def texto(self) -> str:
        """Return the current search text."""
        return self._input.text()

    def definir_texto(self, texto: str) -> None:
        """Set the search text (emits pesquisa_mudou, filtering the list)."""
        self._input.setText(texto or "")

    def limpar(self) -> None:
        """Clear the text."""
        self._input.clear()


class BotaoLimparFiltros(QPushButton):
    """Repor todos os filtros da página, e não só a pesquisa.

    Herdou a função que o pincel tinha nas páginas com filtros (estado,
    cliente, responsável, vista…). Aqui é um botão com nome, ao pé dos filtros
    que repõe — em vez de um ícone ao lado da caixa de pesquisa, que se
    confundia com o ``X`` de limpar o texto.
    """

    def __init__(self, parent=None, *, texto: str = "Limpar filtros") -> None:
        super().__init__(texto, parent)
        self.setToolTip(
            "Repor a pesquisa e todos os filtros desta página (mostrar tudo)"
        )
