"""Reusable helper to build table cells that show their full content on hover.

Adopted as the project default: any textual/numeric cell gets a tooltip with the
complete value, so narrow columns (Observações produção, Descrição no orçamento,
Ref LE, …) stay readable.
"""

from __future__ import annotations

from PySide6.QtWidgets import QTableWidgetItem


def criar_item_tabela(
    texto: object,
    tooltip: str | None = None,
) -> QTableWidgetItem:
    """Create a QTableWidgetItem whose tooltip shows the full cell content.

    ``texto`` is coerced to a display string (None -> ""). When ``tooltip`` is not
    given, the tooltip is the full display text (only set when non-empty).
    """
    display = "" if texto is None else str(texto)
    item = QTableWidgetItem(display)

    conteudo = display if tooltip is None else tooltip
    if conteudo:
        item.setToolTip(conteudo)

    return item
