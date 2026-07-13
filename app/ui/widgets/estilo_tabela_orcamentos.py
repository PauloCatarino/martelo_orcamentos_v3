"""Shared presentation for budget list tables."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QTableWidget

from app.ui import tema


def configurar_tabela_orcamentos(table: QTableWidget, *, compacta: bool = False) -> None:
    """Apply the common modern, dense visual language to a budget table."""
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(25 if compacta else 30)
    table.setStyleSheet(
        f"QTableWidget {{ background: #FFFFFF; alternate-background-color: {tema.BEGE_CLARO};"
        f" border: 1px solid {tema.CINZA_CASTANHO}; border-radius: 6px;"
        " selection-background-color: #D6C2A5; selection-color: #2E2A26;"
        " font-size: 11px; outline: 0; }}\n"
        "QTableWidget::item { padding: 3px 7px; border-bottom: 1px solid #E8E1D7; }\n"
        f"QTableWidget::item:selected {{ background: #D6C2A5; color: {tema.TEXTO_NORMAL}; }}\n"
        f"QHeaderView::section {{ background: {tema.CASTANHO_MEDIO}; color: #FFFFFF;"
        " padding: 6px 7px; border: none; border-right: 1px solid #A99175;"
        " font-weight: bold; }}\n"
        f"QHeaderView::section:hover {{ background: {tema.CASTANHO_ESCURO}; }}"
    )


def aplicar_estilo_linha_orcamento(
    table: QTableWidget,
    row: int,
    *,
    coluna_codigo: int,
    coluna_estado: int,
    estado: str | None,
    coluna_total: int,
    preco_manual: bool = False,
) -> None:
    """Style state, identity and price cells after one row is populated."""
    codigo = table.item(row, coluna_codigo)
    if codigo is not None:
        fonte = QFont(codigo.font())
        fonte.setBold(True)
        codigo.setFont(fonte)
        codigo.setForeground(QColor(tema.CASTANHO_ESCURO))

    estado_item = table.item(row, coluna_estado)
    if estado_item is not None:
        fundo, texto = tema.cor_estado(estado)
        estado_item.setBackground(QColor(fundo))
        estado_item.setForeground(QColor(texto))
        estado_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        fonte = QFont(estado_item.font())
        fonte.setBold(True)
        estado_item.setFont(fonte)

    total = table.item(row, coluna_total)
    if total is not None:
        total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        fonte = QFont(total.font())
        fonte.setBold(True)
        total.setFont(fonte)
        if preco_manual:
            total.setBackground(QColor(tema.OCRE_SUAVE))
            total.setForeground(QColor(tema.OCRE_ESCURO))
            total.setToolTip("Inclui preço manual — valor não totalmente calculado pelo custeio.")
