"""Tests for the fast-edit Enter/Tab navigation (phase 8V.1 / 8V.1 fix)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from app.ui.pages.orcamento_item_custeio_page import (
    CusteioEnterDelegate,
    CusteioLinhasTable,
)

_app = QApplication.instance() or QApplication([])

# Header layout: the six fast-flow columns plus a NON-flow column at the end.
_HEADERS = ["Descrição livre", "QT mod", "QT und", "Comp", "Larg", "Esp", "Fator série"]
_FATOR_SERIE = 6


def _item(editavel: bool) -> QTableWidgetItem:
    item = QTableWidgetItem("x")
    if editavel:
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
    else:
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def _tabela() -> CusteioLinhasTable:
    """2 rows. Row 0: QT mod read-only (division-like-ish); both rows have an
    editable "Fator série" that must NEVER be visited by Enter/Tab."""
    tabela = CusteioLinhasTable(2, len(_HEADERS))
    tabela.setHorizontalHeaderLabels(_HEADERS)
    # Row 0: Descrição livre E, QT mod RO, QT und E, Comp E, Larg E, Esp E, Fator E
    for col, editavel in enumerate([True, False, True, True, True, True, True]):
        tabela.setItem(0, col, _item(editavel))
    # Row 1: all fast-flow editable; Fator série editable too.
    for col in range(len(_HEADERS)):
        tabela.setItem(1, col, _item(True))
    return tabela


def test_colunas_fluxo_rapido_exclui_fora_do_conjunto() -> None:
    tabela = _tabela()
    # Resolved from the headers: the six flow columns, in order; NOT Fator série.
    assert tabela._colunas_fluxo_rapido() == [0, 1, 2, 3, 4, 5]
    assert _FATOR_SERIE not in tabela._colunas_fluxo_rapido()


def test_proxima_salta_coluna_read_only_do_conjunto() -> None:
    tabela = _tabela()
    # From Descrição livre (0): QT mod (1) is read-only here -> QT und (2).
    assert tabela._proxima_celula_editavel(0, 0) == (0, 2)


def test_proxima_faz_wrap_para_descricao_livre_da_linha_seguinte() -> None:
    tabela = _tabela()
    # From Esp (5, last flow column): no flow column to the right (Fator série
    # is outside the set) -> wrap to the first flow column of row 1.
    assert tabela._proxima_celula_editavel(0, 5) == (1, 0)


def test_nunca_devolve_fator_serie_nem_colunas_fora_do_conjunto() -> None:
    tabela = _tabela()
    # Walk the whole flow from the start and ensure Fator série never appears.
    visitadas = []
    pos = (0, 0)
    for _ in range(20):
        proxima = tabela._proxima_celula_editavel(*pos)
        if proxima is None:
            break
        visitadas.append(proxima)
        pos = proxima
    assert all(col != _FATOR_SERIE for _row, col in visitadas)
    # Even starting ON Fator série, Enter leaves the set (wraps to next row).
    assert tabela._proxima_celula_editavel(0, _FATOR_SERIE) == (1, 0)


def test_proxima_none_no_fim() -> None:
    tabela = _tabela()
    # Last editable flow cell of the last row -> nothing more.
    assert tabela._proxima_celula_editavel(1, 5) is None
    assert tabela._proxima_celula_editavel(-1, 0) is None


def test_celula_editavel_trata_celula_vazia() -> None:
    tabela = _tabela()
    tabela.setItem(0, 3, None)  # remove the Comp item on row 0
    assert tabela._celula_editavel(0, 0) is True
    assert tabela._celula_editavel(0, 1) is False  # read-only
    assert tabela._celula_editavel(0, 3) is False  # no item


def test_tabela_instala_delegate_de_enter() -> None:
    tabela = _tabela()
    assert isinstance(tabela.itemDelegate(), CusteioEnterDelegate)
