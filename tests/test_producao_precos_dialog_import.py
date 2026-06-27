"""Import checks for the production price validation dialog."""

from __future__ import annotations

import inspect


def test_producao_precos_dialog_imports_and_has_selection_api() -> None:
    from app.ui.dialogs.producao_precos_dialog import ProducaoPrecosDialog

    source = inspect.getsource(ProducaoPrecosDialog)

    assert "QDialog" in source
    assert "QTableWidget" in source
    assert "ItemIsUserCheckable" in source
    assert '"Pre\\u00e7o Martelo"' in source
    assert '"Pre\\u00e7o externo"' in source
    assert '"Atualizar selecionados"' in source
    assert hasattr(ProducaoPrecosDialog, "selecionados")
