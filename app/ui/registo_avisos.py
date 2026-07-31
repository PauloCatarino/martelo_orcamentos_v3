"""Registar no diário tudo o que o Martelo mostra ao utilizador.

O V3 tem mais de uma centena de sítios a abrir caixas de aviso. Em vez de lhes
tocar uma a uma (e de alguém se esquecer da próxima), fica aqui um filtro de
eventos na aplicação: sempre que uma QMessageBox aparece, o título, o texto e a
gravidade vão para o diário. Assim, quando um utilizador diz "deu um erro", há
no ficheiro exatamente o que ele viu no ecrã, à hora a que viu.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QMessageBox

from app.core import diario_bordo


class _RegistoDeAvisos(QObject):
    """Watch every message box the application shows."""

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt)
        try:
            if event.type() == QEvent.Type.Show and isinstance(obj, QMessageBox):
                self._registar(obj)
        except Exception:  # noqa: BLE001 - registar nunca pode partir a UI
            pass
        return False

    @staticmethod
    def _registar(caixa: QMessageBox) -> None:
        titulo = caixa.windowTitle() or "(sem título)"
        texto = " ".join(filter(None, (caixa.text(), caixa.informativeText())))
        icone = caixa.icon()
        if icone == QMessageBox.Icon.Critical:
            diario_bordo.registar_erro(titulo, texto)
        elif icone == QMessageBox.Icon.Warning:
            diario_bordo.registar_aviso(titulo, texto)
        else:
            # Perguntas e confirmações também contam: dizem o que foi decidido.
            diario_bordo.registar_acao(f"Mensagem '{titulo}'", texto)


_filtro: _RegistoDeAvisos | None = None


def instalar_registo_de_avisos(qt_app) -> None:
    """Install the watcher on the application (call once, at start-up)."""
    global _filtro

    if _filtro is not None:
        return
    _filtro = _RegistoDeAvisos()
    qt_app.installEventFilter(_filtro)
