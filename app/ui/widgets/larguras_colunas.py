"""Persist table column widths per machine (QSettings)."""

from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QTableView, QTableWidget

_ORG = "Lanca Encanto"
_APP = "Martelo Orcamentos V3"


def ligar_persistencia_larguras(table: QTableView | QTableWidget, chave: str) -> None:
    """Restaura as larguras guardadas de ``table`` e persiste as futuras.

    Guardado localmente (QSettings) para cada máquina/ecrã manter as suas larguras.
    ``chave`` tem de ser único por tabela (ex.: "clientes_temporarios").
    """
    header = table.horizontalHeader()

    settings = QSettings(_ORG, _APP)
    for col in range(header.count()):
        largura = _para_int(settings.value(f"larguras/{chave}/{col}"))
        if largura and largura > 0:
            header.resizeSection(col, largura)

    def _guardar(indice: int, _antiga: int, nova: int) -> None:
        if nova > 0:
            QSettings(_ORG, _APP).setValue(f"larguras/{chave}/{indice}", int(nova))

    header.sectionResized.connect(_guardar)


def _para_int(valor) -> int | None:
    if valor is None:
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None
