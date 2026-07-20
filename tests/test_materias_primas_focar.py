"""Fase 3B: destacar a matéria-prima exata (por Ref LE) na página Matérias-Primas."""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from app.ui.pages.materias_primas_page import MateriasPrimasPage

_app = QApplication.instance() or QApplication([])


def _tabela_com_refs(refs: list[str]) -> QTableWidget:
    table = QTableWidget(len(refs), 1)
    for row, ref in enumerate(refs):
        table.setItem(row, 0, QTableWidgetItem(ref))
    return table


def test_focar_materia_prima_seleciona_a_linha_certa() -> None:
    table = _tabela_com_refs(["PLC0001", "PLC0033", "PLC0099"])
    piscadas: list[int] = []
    fake = SimpleNamespace(
        campo_pesquisa=SimpleNamespace(definir_texto=lambda _t: None),
        table=table,
        _piscar_linha=lambda row: piscadas.append(row),
    )

    MateriasPrimasPage.focar_materia_prima(fake, "plc0033")  # case-insensitive

    assert table.currentRow() == 1
    assert piscadas == [1]


def test_focar_materia_prima_ignora_ref_vazia() -> None:
    table = _tabela_com_refs(["PLC0001"])
    chamou_pesquisa: list[str] = []
    fake = SimpleNamespace(
        campo_pesquisa=SimpleNamespace(definir_texto=chamou_pesquisa.append),
        table=table,
        _piscar_linha=lambda row: None,
    )

    MateriasPrimasPage.focar_materia_prima(fake, None)

    assert chamou_pesquisa == []  # nem sequer filtra
