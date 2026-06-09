"""Tests for the reusable table-cell helper with tooltips (phase 8P)."""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def test_criar_item_tabela_define_tooltip_com_texto_completo() -> None:
    from app.ui.widgets.table_item import criar_item_tabela

    texto = "Área de acabamento não calculada: dimensões Comp/Larg em falta."
    item = criar_item_tabela(texto)

    assert item.text() == texto
    assert item.toolTip() == texto


def test_criar_item_tabela_texto_vazio_sem_tooltip() -> None:
    from app.ui.widgets.table_item import criar_item_tabela

    item = criar_item_tabela("")
    assert item.text() == ""
    assert item.toolTip() == ""


def test_criar_item_tabela_none_vira_vazio() -> None:
    from app.ui.widgets.table_item import criar_item_tabela

    item = criar_item_tabela(None)
    assert item.text() == ""


def test_criar_item_tabela_tooltip_personalizado() -> None:
    from app.ui.widgets.table_item import criar_item_tabela

    item = criar_item_tabela("LACAGEM...", tooltip="LACAGEM BRANCA MATE")
    assert item.text() == "LACAGEM..."
    assert item.toolTip() == "LACAGEM BRANCA MATE"


def test_custeio_page_usa_helper_de_tooltip() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage._preencher_tabela)
    assert "criar_item_tabela" in source


def test_picker_usa_helper_de_tooltip() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    source = inspect.getsource(MateriaPrimaPickerDialog._preencher)
    assert "criar_item_tabela" in source
