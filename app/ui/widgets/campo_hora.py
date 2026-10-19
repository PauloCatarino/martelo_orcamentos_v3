"""Campo de hora que pode ficar vazio («--:--»).

O ``QTimeEdit`` tem sempre uma hora. Numa linha Entrada/Saída de um sábado em
que não se trabalhou, ou numa linha acabada de acrescentar com o «+», o campo
tem de poder ficar vazio — senão o Martelo contava horas que ninguém fez.

Este campo tem as setas do ``QTimeEdit`` (na parte das horas sobe/desce uma
hora; na dos minutos, 15 minutos), aceita escrever «8», «830», «8:30», «17h»
e, como os outros campos do Martelo, só responde à roda do rato quando tem o
foco.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractSpinBox

from app.domain import registo_horas as regra

#: Quando o campo está vazio, a primeira seta põe esta hora.
HORA_INICIAL = 8 * 60


def ler(texto: str | None) -> int | None:
    """«8», «830», «0830», «8:30», «17h» → minutos; ``None`` se vazio ou inválido."""
    valor = (texto or "").strip()
    if re.fullmatch(r"\d{3,4}", valor):
        valor = f"{valor[:-2]}:{valor[-2:]}"
    minutos = regra.ler_hora(valor)
    # 24:00 é a meia-noite: no campo escreve-se 00:00.
    return None if minutos is None else minutos % regra.MINUTOS_DIA


class CampoHora(QAbstractSpinBox):
    #: O valor mudou (a escrever, nas setas ou por código).
    alterado = Signal()
    #: A pessoa mexeu no campo (escreveu ou usou as setas).
    editado = Signal()

    def __init__(
        self,
        parent=None,
        *,
        tooltip: str = "",
        sugestao: Callable[[], int | None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._minutos: int | None = None
        self._sugestao = sugestao
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.setAccelerated(True)
        # As setas do Windows 11 ocupam metade do campo: menos do que isto corta
        # o primeiro algarismo («8:00» em vez de «08:00»).
        self.setMinimumWidth(112)
        self.lineEdit().setPlaceholderText("--:--")
        self.lineEdit().setMaxLength(5)
        if tooltip:
            self.setToolTip(tooltip)
        self.lineEdit().textChanged.connect(self._ao_mudar_texto)
        self.lineEdit().textEdited.connect(lambda _t: self.editado.emit())
        self.editingFinished.connect(self._arrumar)

    # ------------------------------------------------------------------
    def minutos(self) -> int | None:
        return self._minutos

    def definir(self, minutos: int | None) -> None:
        """Põe a hora (minutos desde a meia-noite) ou deixa o campo vazio."""
        self.lineEdit().setText(regra.hora_texto(minutos) if minutos is not None else "")

    def invalido(self) -> bool:
        """Tem texto que não é uma hora (ex.: «25:00», «abc»)."""
        return bool(self.text().strip()) and self._minutos is None

    def clear(self) -> None:  # noqa: D102 - mesmo nome do Qt
        self.definir(None)

    # ------------------------------------------------------------------
    def _ao_mudar_texto(self, texto: str) -> None:
        self._minutos = ler(texto)
        self.alterado.emit()

    def _arrumar(self) -> None:
        if self._minutos is not None and self.text() != regra.hora_texto(self._minutos):
            self.definir(self._minutos)

    def stepEnabled(self):  # noqa: N802 (Qt naming)
        if self.isReadOnly() or not self.isEnabled():
            return QAbstractSpinBox.StepEnabledFlag.StepNone
        return (
            QAbstractSpinBox.StepEnabledFlag.StepUpEnabled
            | QAbstractSpinBox.StepEnabledFlag.StepDownEnabled
        )

    def stepBy(self, passos: int) -> None:  # noqa: N802 (Qt naming)
        cursor = self.lineEdit().cursorPosition()
        if self._minutos is None:
            sugestao = self._sugestao() if self._sugestao is not None else None
            novo = sugestao if sugestao is not None else HORA_INICIAL
        else:
            passo = 60 if cursor <= 2 else 15
            novo = (self._minutos + passos * passo) % regra.MINUTOS_DIA
        self.definir(novo)
        self.lineEdit().setCursorPosition(cursor)
        self.editado.emit()

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self.hasFocus():
            super().wheelEvent(event)
            return
        event.ignore()
