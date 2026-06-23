"""Persist QSplitter sizes per machine (QSettings)."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtWidgets import QSplitter

_ORG = "Lanca Encanto"
_APP = "Martelo Orcamentos V3"


def ligar_persistencia_splitter(splitter: QSplitter, chave: str) -> bool:
    """Restaura/persiste as alturas (sizes) de um ``QSplitter``.

    Guardado localmente (QSettings) por máquina. Devolve ``True`` se restaurou
    um estado guardado (útil para só aplicar proporções por defeito quando ainda
    não há nada guardado).
    """
    estado = QSettings(_ORG, _APP).value(f"splitters/{chave}")
    if isinstance(estado, (bytes, bytearray)):
        estado = QByteArray(estado)

    restaurou = False
    if isinstance(estado, QByteArray) and not estado.isEmpty():
        restaurou = bool(splitter.restoreState(estado))

    def _guardar(_pos: int, _index: int) -> None:
        QSettings(_ORG, _APP).setValue(f"splitters/{chave}", splitter.saveState())

    splitter.splitterMoved.connect(_guardar)
    return restaurou
