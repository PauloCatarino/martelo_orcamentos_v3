"""Persist table column widths per machine and per authenticated user (QSettings)."""

from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QHeaderView, QTableView, QTableWidget, QTreeView

from app.core.session import app_session

_ORG = "Lanca Encanto"
_APP = "Martelo Orcamentos V3"


def ligar_persistencia_larguras(
    table: QTableView | QTableWidget | QTreeView,
    chave: str,
    *,
    forcar_interativas: bool = True,
    guardar_ordem: bool = False,
) -> bool:
    """Restaura/persiste as larguras das colunas REDIMENSIONÁVEIS de ``table``.

    Guardado localmente (QSettings) por máquina e por utilizador autenticado
    (sem sessão, usa "default"). Colunas em modo Stretch/ResizeToContents são
    ignoradas (a sua largura é automática).

    Quando ``guardar_ordem`` está ativo, o utilizador também pode arrastar os
    cabeçalhos e a ordem visual fica guardada com a mesma separação por
    utilizador.

    Devolve ``True`` se restaurou alguma largura ou ordem guardada (útil para
    tabelas que semeiam larguras-por-conteúdo só quando ainda não há nada
    guardado).
    """
    # QTableView/QTableWidget expose ``horizontalHeader()``, while QTreeView
    # and QTreeWidget expose the same QHeaderView through ``header()``.
    if isinstance(table, QTreeView):
        header = table.header()
    else:
        header = table.horizontalHeader()
    interativo = QHeaderView.ResizeMode.Interactive

    if forcar_interativas:
        for col in range(header.count()):
            header.setSectionResizeMode(col, interativo)
        header.setStretchLastSection(False)

    restaurou = False
    settings = QSettings(_ORG, _APP)
    for col in range(header.count()):
        if header.sectionResizeMode(col) != interativo:
            continue
        largura = _para_int(settings.value(_chave_larguras(chave, col)))
        if largura and largura > 0:
            header.resizeSection(col, largura)
            restaurou = True

    if guardar_ordem:
        header.setSectionsMovable(True)
        ordem = _para_lista_int(settings.value(_chave_ordem(chave)))
        if ordem is not None and sorted(ordem) == list(range(header.count())):
            for posicao_visual, indice_logico in enumerate(ordem):
                posicao_atual = header.visualIndex(indice_logico)
                if posicao_atual != posicao_visual:
                    header.moveSection(posicao_atual, posicao_visual)
            restaurou = True

    def _guardar(indice: int, _antiga: int, nova: int) -> None:
        if header.sectionResizeMode(indice) != interativo:
            return
        if nova > 0:
            QSettings(_ORG, _APP).setValue(_chave_larguras(chave, indice), int(nova))

    header.sectionResized.connect(_guardar)

    if guardar_ordem:

        def _guardar_ordem(
            _indice_logico: int,
            _posicao_antiga: int,
            _posicao_nova: int,
        ) -> None:
            ordem_atual = [
                header.logicalIndex(posicao_visual)
                for posicao_visual in range(header.count())
            ]
            QSettings(_ORG, _APP).setValue(_chave_ordem(chave), ordem_atual)

        header.sectionMoved.connect(_guardar_ordem)
    return restaurou


def _chave_larguras(chave: str, indice: int) -> str:
    return f"larguras/{_utilizador_atual()}/{chave}/{indice}"


def _chave_ordem(chave: str) -> str:
    return f"ordem_colunas/{_utilizador_atual()}/{chave}"


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


def _para_lista_int(valor) -> list[int] | None:
    if not isinstance(valor, (list, tuple)):
        return None
    try:
        return [int(item) for item in valor]
    except (TypeError, ValueError):
        return None
