"""Persist table column widths per machine and per authenticated user (QSettings)."""

from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QHeaderView, QTableView, QTableWidget

from app.core.session import app_session

_ORG = "Lanca Encanto"
_APP = "Martelo Orcamentos V3"


def ligar_persistencia_larguras(table: QTableView | QTableWidget, chave: str) -> bool:
    """Restaura/persiste as larguras das colunas REDIMENSIONÁVEIS de ``table``.

    Guardado localmente (QSettings) por máquina e por utilizador autenticado
    (sem sessão, usa "default"). Colunas em modo Stretch/ResizeToContents são
    ignoradas (a sua largura é automática).

    Devolve ``True`` se restaurou alguma largura guardada (útil para tabelas que
    semeiam larguras-por-conteúdo só quando ainda não há nada guardado).
    """
    header = table.horizontalHeader()
    interativo = QHeaderView.ResizeMode.Interactive

    restaurou = False
    settings = QSettings(_ORG, _APP)
    for col in range(header.count()):
        if header.sectionResizeMode(col) != interativo:
            continue
        largura = _para_int(settings.value(_chave_larguras(chave, col)))
        if largura and largura > 0:
            header.resizeSection(col, largura)
            restaurou = True

    def _guardar(indice: int, _antiga: int, nova: int) -> None:
        if header.sectionResizeMode(indice) != interativo:
            return
        if nova > 0:
            QSettings(_ORG, _APP).setValue(_chave_larguras(chave, indice), int(nova))

    header.sectionResized.connect(_guardar)
    return restaurou


def _chave_larguras(chave: str, indice: int) -> str:
    return f"larguras/{_utilizador_atual()}/{chave}/{indice}"


def _utilizador_atual() -> str:
    """Return the current authenticated username, or "default" without a session."""
    username = getattr(app_session.current_user, "username", None)
    return username or "default"


def _para_int(valor) -> int | None:
    if valor is None:
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None
