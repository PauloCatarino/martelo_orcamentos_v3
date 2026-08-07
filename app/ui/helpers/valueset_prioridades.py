"""Aviso visual comum para prioridades ValueSet repetidas após colagem."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QBrush, QColor

from app.domain.valueset_prioridades import detetar_conflito_prioridade


def avisar_prioridade_repetida_apos_colagem(
    page,
    *,
    table,
    headers: list[str],
    linhas_by_row: dict,
    linha_id: int,
) -> str | None:
    """Seleciona e faz piscar a prioridade em conflito; devolve o aviso."""
    destino = next(
        (linha for linha in linhas_by_row.values() if linha.id == linha_id), None
    )
    if destino is None:
        return None

    conflito = detetar_conflito_prioridade(destino, linhas_by_row.values())
    if conflito is None:
        return None

    row = next(row for row, linha in linhas_by_row.items() if linha.id == linha_id)
    coluna = headers.index("Prioridade")
    item = table.item(row, coluna)
    if item is not None:
        item.setToolTip(
            f"Prioridade repetida. Altere este valor; sugestão: {conflito.sugestao}."
        )
        table.setCurrentCell(row, coluna)
        table.scrollToItem(item)
        normal = QBrush(item.background())
        alerta = QBrush(QColor("#ffb3b3"))
        contador = {"valor": 0}
        timer = QTimer(page)
        timer.setInterval(220)

        def alternar() -> None:
            contador["valor"] += 1
            item.setBackground(alerta if contador["valor"] % 2 else normal)
            if contador["valor"] >= 8:
                timer.stop()
                item.setBackground(alerta)

        timer.timeout.connect(alternar)
        timer.start()
        page._prioridade_flash_timer = timer

    return (
        f"A prioridade {conflito.prioridade} ficou repetida na chave "
        f"{conflito.chave}. Altere-a; sugestão: {conflito.sugestao}."
    )
