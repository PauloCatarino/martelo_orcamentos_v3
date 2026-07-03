"""Import checks for the production PHC sync dialog."""

from __future__ import annotations

import inspect


def test_producao_phc_sync_dialog_imports_and_has_selection_api() -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    source = inspect.getsource(ProducaoPhcSyncDialog)

    assert "QDialog" in source
    assert "QTableWidget" in source
    assert "ItemIsUserCheckable" in source
    assert '"N\\u00ba Enc PHC"' in source
    assert '"Fonte"' in source
    assert '"Atualizar selecionados"' in source
    assert hasattr(ProducaoPhcSyncDialog, "selecionados")
