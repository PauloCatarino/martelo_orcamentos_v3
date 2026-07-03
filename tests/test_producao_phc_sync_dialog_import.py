"""Import checks for the production PHC sync dialog."""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def test_producao_phc_sync_dialog_imports_and_has_selection_api() -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    source = inspect.getsource(ProducaoPhcSyncDialog)

    assert "QDialog" in source
    assert "QTableWidget" in source
    assert "ItemIsUserCheckable" in source
    assert '"N\\u00ba Enc PHC"' in source
    assert '"Fonte"' in source
    assert '"Selecionar tudo"' in source
    assert '"Desmarcar tudo"' in source
    assert '"Atualizar selecionados"' in source
    assert hasattr(ProducaoPhcSyncDialog, "_selecionar_tudo")
    assert hasattr(ProducaoPhcSyncDialog, "_desmarcar_tudo")
    assert hasattr(ProducaoPhcSyncDialog, "selecionados")


def test_producao_phc_sync_dialog_seleciona_e_desmarca_tudo() -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    diffs = [
        {
            "id": 1,
            "codigo": "26.1001_01_01_CLIENTE",
            "num_enc_phc": "1001",
            "fonte": "PHC",
            "cliente": "Cliente 1",
            "estado_martelo": "Desenho",
            "estado_sugerido": "Producao",
            "estado_phc_raw": "Em Producao",
        },
        {
            "id": 2,
            "codigo": "26._118_01_01_CLIENTE",
            "num_enc_phc": "_118",
            "fonte": "Streamlit",
            "cliente": "Cliente 2",
            "estado_martelo": "Desenho",
            "estado_sugerido": "Finalizado",
            "estado_phc_raw": "Finalizada",
        },
    ]
    dialog = ProducaoPhcSyncDialog(diffs)

    assert all(
        dialog.table.item(row, 0).checkState() == Qt.CheckState.Checked
        for row in range(dialog.table.rowCount())
    )

    dialog._desmarcar_tudo()

    assert all(
        dialog.table.item(row, 0).checkState() == Qt.CheckState.Unchecked
        for row in range(dialog.table.rowCount())
    )
    assert dialog.selecionados() == []

    dialog._selecionar_tudo()

    assert all(
        dialog.table.item(row, 0).checkState() == Qt.CheckState.Checked
        for row in range(dialog.table.rowCount())
    )
    assert dialog.selecionados() == [(1, "Producao"), (2, "Finalizado")]
