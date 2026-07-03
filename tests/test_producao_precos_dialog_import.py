"""Import checks for the production price validation dialog."""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def test_producao_precos_dialog_imports_and_has_selection_api() -> None:
    from app.ui.dialogs.producao_precos_dialog import ProducaoPrecosDialog

    source = inspect.getsource(ProducaoPrecosDialog)

    assert "QDialog" in source
    assert "QTableWidget" in source
    assert "ItemIsUserCheckable" in source
    assert '"Pre\\u00e7o Martelo"' in source
    assert '"Pre\\u00e7o externo"' in source
    assert '"Selecionar tudo"' in source
    assert '"Desmarcar tudo"' in source
    assert '"Atualizar selecionados"' in source
    assert hasattr(ProducaoPrecosDialog, "_selecionar_tudo")
    assert hasattr(ProducaoPrecosDialog, "_desmarcar_tudo")
    assert hasattr(ProducaoPrecosDialog, "selecionados")


def test_producao_precos_dialog_seleciona_e_desmarca_tudo() -> None:
    from app.ui.dialogs.producao_precos_dialog import ProducaoPrecosDialog

    diffs = [
        {
            "id": 1,
            "codigo": "26.1001_01_01_CLIENTE",
            "num_enc": "1001",
            "fonte": "PHC",
            "cliente": "Cliente 1",
            "preco_martelo": None,
            "preco_externo": 123.45,
            "default_check": True,
        },
        {
            "id": 2,
            "codigo": "26._118_01_01_CLIENTE",
            "num_enc": "_118",
            "fonte": "Streamlit",
            "cliente": "Cliente 2",
            "preco_martelo": 100.0,
            "preco_externo": 250.0,
            "default_check": False,
        },
    ]
    dialog = ProducaoPrecosDialog(diffs)

    assert dialog.table.item(0, 0).checkState() == Qt.CheckState.Checked
    assert dialog.table.item(1, 0).checkState() == Qt.CheckState.Unchecked

    dialog._selecionar_tudo()

    assert all(
        dialog.table.item(row, 0).checkState() == Qt.CheckState.Checked
        for row in range(dialog.table.rowCount())
    )
    assert dialog.selecionados() == [(1, 123.45), (2, 250.0)]

    dialog._desmarcar_tudo()

    assert all(
        dialog.table.item(row, 0).checkState() == Qt.CheckState.Unchecked
        for row in range(dialog.table.rowCount())
    )
    assert dialog.selecionados() == []
