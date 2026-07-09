"""Shared visual styling for ValueSet line tables."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from app.ui.tema import (
    CASTANHO_ESCURO,
    CASTANHO_MEDIO,
    CINZA_ESCURO,
    ESTILO_TABELA_CONFIG_CABECALHO,
    OCRE_ESCURO,
    OCRE_SUAVE,
    TEXTO_NORMAL,
    VERDE_ESCURO,
    VERMELHO_ESCURO,
    cor_grupo_chave,
)
from app.ui.widgets.colunas_visiveis import ligar_menu_colunas

TOOLTIP_EDITADO_LOCALMENTE = (
    "Linha editada localmente — já não corresponde ao original importado."
)


@dataclass(frozen=True)
class EstadoLinhaValueset:
    """Presentation metadata for one ValueSet line."""

    linha: Any
    indice_grupo: int
    primeira_do_grupo: bool
    chave_normalizada: str
    fundo_grupo: str
    prioridade_um: bool
    editado_localmente: bool
    ativo: bool


def preparar_linhas_valueset(linhas: list[Any]) -> list[EstadoLinhaValueset]:
    """Return sorted ValueSet lines with grouping and visual flags."""
    linhas_ordenadas = sorted(linhas, key=_sort_key)
    estados: list[EstadoLinhaValueset] = []
    chave_anterior: str | None = None
    indice_grupo = -1

    for linha in linhas_ordenadas:
        chave = _normalizar_chave(getattr(linha, "chave", None))
        primeira_do_grupo = chave != chave_anterior
        if primeira_do_grupo:
            indice_grupo += 1
            chave_anterior = chave

        prioridade = getattr(linha, "prioridade", None)
        ativo = bool(getattr(linha, "ativo", True))
        editado = bool(getattr(linha, "editado_localmente", False))
        estados.append(
            EstadoLinhaValueset(
                linha=linha,
                indice_grupo=indice_grupo,
                primeira_do_grupo=primeira_do_grupo,
                chave_normalizada=chave,
                fundo_grupo=cor_grupo_chave(indice_grupo),
                prioridade_um=prioridade == 1,
                editado_localmente=editado,
                ativo=ativo,
            )
        )

    return estados


def texto_chave_valueset(estado: EstadoLinhaValueset) -> str:
    """Return the key cell text, visible only on the first row of each group."""
    if not estado.primeira_do_grupo:
        return ""
    return getattr(estado.linha, "chave", None) or ""


def texto_opcao_valueset(estado: EstadoLinhaValueset, texto: str) -> str:
    """Return the option text with a local-edit mark when needed."""
    if estado.editado_localmente:
        return f"✎ {texto}"
    return texto


def texto_prioridade_valueset(estado: EstadoLinhaValueset) -> str:
    """Return priority text, using an em dash when no priority is defined."""
    prioridade = getattr(estado.linha, "prioridade", None)
    return "—" if prioridade is None else str(prioridade)


def texto_editado_valueset(estado: EstadoLinhaValueset) -> str:
    """Return the display text for the local-edit column."""
    return "✎ Sim" if estado.editado_localmente else "—"


def texto_ativo_valueset(estado: EstadoLinhaValueset) -> str:
    """Return the display text for the active column."""
    return "✓" if estado.ativo else "✗"


def configurar_tabela_valueset(table: QTableWidget, chave_colunas: str) -> None:
    """Apply the shared ValueSet table style and column visibility menu."""
    table.setAlternatingRowColors(False)
    table.setStyleSheet(ESTILO_TABELA_CONFIG_CABECALHO)
    ligar_menu_colunas(table, chave_colunas)


def aplicar_estilo_item_valueset(
    item: QTableWidgetItem,
    nome_coluna: str,
    estado: EstadoLinhaValueset,
) -> None:
    """Apply the shared ValueSet cell style to one item."""
    item.setBackground(QBrush(QColor(estado.fundo_grupo)))
    item.setForeground(QBrush(QColor(TEXTO_NORMAL)))

    if not estado.ativo:
        _set_text_color(item, CINZA_ESCURO)
        _set_italic(item, True)

    if nome_coluna == "Chave":
        _set_text_color(item, CASTANHO_ESCURO)
        if estado.primeira_do_grupo:
            _set_bold(item, True)
        return

    if nome_coluna == "Opção" and estado.editado_localmente:
        item.setBackground(QBrush(QColor(OCRE_SUAVE)))
        _set_text_color(item, OCRE_ESCURO)
        _set_bold(item, True)
        item.setToolTip(TOOLTIP_EDITADO_LOCALMENTE)
        return

    if nome_coluna == "Ref LE":
        _set_text_color(item, CASTANHO_MEDIO)
        return

    if nome_coluna == "Unidade":
        _align_center(item)
        return

    if nome_coluna in {"Preço tabela", "Preço líquido"}:
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        if nome_coluna == "Preço líquido":
            _set_bold(item, True)
        return

    if nome_coluna == "Prioridade":
        _align_center(item)
        if estado.prioridade_um:
            item.setBackground(QBrush(QColor(CASTANHO_ESCURO)))
            _set_text_color(item, "#FFFFFF")
            _set_bold(item, True)
        else:
            _set_text_color(item, CASTANHO_MEDIO)
        return

    if nome_coluna == "Editado localmente":
        _align_center(item)
        if estado.editado_localmente:
            item.setBackground(QBrush(QColor(OCRE_SUAVE)))
            _set_text_color(item, OCRE_ESCURO)
            _set_bold(item, True)
            item.setToolTip(TOOLTIP_EDITADO_LOCALMENTE)
        else:
            _set_text_color(item, CINZA_ESCURO)
        return

    if nome_coluna == "Ativo":
        _align_center(item)
        _set_text_color(item, VERDE_ESCURO if estado.ativo else VERMELHO_ESCURO)
        _set_bold(item, True)
        return

    if nome_coluna == "Operações":
        _set_text_color(item, VERDE_ESCURO)


def _sort_key(linha: Any) -> tuple:
    prioridade = getattr(linha, "prioridade", None)
    ordem = getattr(linha, "ordem", None)
    linha_id = getattr(linha, "id", None)
    return (
        _normalizar_chave(getattr(linha, "chave", None)),
        prioridade is None,
        _numero_ordenacao(prioridade),
        _numero_ordenacao(ordem),
        _numero_ordenacao(linha_id),
    )


def _normalizar_chave(chave: str | None) -> str:
    return (chave or "").strip().upper()


def _numero_ordenacao(valor) -> int:
    if valor is None:
        return 0
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 0


def _set_bold(item: QTableWidgetItem, bold: bool) -> None:
    font = item.font()
    font.setBold(bold)
    item.setFont(font)


def _set_italic(item: QTableWidgetItem, italic: bool) -> None:
    font = item.font()
    font.setItalic(italic)
    item.setFont(font)


def _set_text_color(item: QTableWidgetItem, color: str) -> None:
    item.setForeground(QBrush(QColor(color)))


def _align_center(item: QTableWidgetItem) -> None:
    item.setTextAlignment(
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
    )
