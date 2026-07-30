"""Realce da célula sob o rato: fundo castanho escuro, texto branco.

Numa lista larga (a dos Clientes tem 12 colunas) perde-se a linha de vista a
meio do ecrã. Um simples fundo mais escuro não chegava — o texto castanho
ficava ilegível —, por isso o texto passa a branco no mesmo movimento.

Feito num delegate e não por stylesheet porque as células com cor própria
(``setBackground``) ganhariam à folha de estilos e ficariam sem realce.
"""

from __future__ import annotations

from PySide6.QtGui import QBrush, QColor, QPalette
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from app.ui import tema

TEXTO_REALCE = "#FFFFFF"


class RealceRatoDelegate(QStyledItemDelegate):
    """Paint the cell under the mouse in dark brown with white text."""

    def initStyleOption(self, option, index) -> None:  # noqa: N802 - API do Qt
        super().initStyleOption(option, index)

        if not option.state & QStyle.StateFlag.State_MouseOver:
            return

        option.backgroundBrush = QBrush(QColor(tema.CASTANHO_ESCURO))
        branco = QColor(TEXTO_REALCE)
        option.palette.setColor(QPalette.ColorRole.Text, branco)
        option.palette.setColor(QPalette.ColorRole.HighlightedText, branco)
