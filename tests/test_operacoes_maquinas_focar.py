"""Fase 3B: destacar a máquina relevante (por categoria) em Máquinas/Tarifas."""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QWidget,
)

from app.ui.pages.operacoes_maquinas_page import OperacoesMaquinasPage

_app = QApplication.instance() or QApplication([])


def _fake_page(maquinas):
    table = QTableWidget(len(maquinas), 1)
    por_row = {}
    for row, maq in enumerate(maquinas):
        table.setItem(row, 0, QTableWidgetItem(maq.codigo))
        por_row[row] = maq
    tabs = QTabWidget()
    tabs.addTab(QWidget(), "Operações")
    tabs.addTab(QWidget(), "Máquinas")
    piscadas: list[int] = []
    return SimpleNamespace(
        maquinas_table=table,
        _maquinas_by_row=por_row,
        tabs=tabs,
        _piscar_linha_maquina=piscadas.append,
    ), tabs, piscadas


def test_focar_maquina_seleciona_pela_categoria() -> None:
    maquinas = [
        SimpleNamespace(codigo="CORTE_01", nome="Serra", tipo="CORTE"),
        SimpleNamespace(codigo="CNC_VERTICAL", nome="CNC", tipo="CNC"),
    ]
    fake, tabs, piscadas = _fake_page(maquinas)

    OperacoesMaquinasPage.focar_maquina(fake, "CNC")

    assert fake.maquinas_table.currentRow() == 1
    assert tabs.currentIndex() == 1  # mudou para o separador Máquinas
    assert piscadas == [1]


def test_focar_maquina_ignora_termo_vazio() -> None:
    fake, _tabs, piscadas = _fake_page(
        [SimpleNamespace(codigo="CNC_VERTICAL", nome="CNC", tipo="CNC")]
    )
    OperacoesMaquinasPage.focar_maquina(fake, None)
    assert piscadas == []
