"""Import checks for the new production version dialog."""

from __future__ import annotations

import inspect


def test_nova_versao_processo_dialog_imports_expected_widgets() -> None:
    from app.ui.dialogs.nova_versao_processo_dialog import NovaVersaoProcessoDialog

    source = inspect.getsource(NovaVersaoProcessoDialog)

    assert "Sugestão Obra" in source
    assert "Sugestão CUT-RITE" in source
    assert "QIntValidator" in source
    assert "QTimer" in source
    assert "QTreeWidget" in source
    assert "Pastas existentes (Servidor)" in source
    assert "values" in source
    assert "já existe" in source
    assert hasattr(NovaVersaoProcessoDialog, "_start_blink")
    assert hasattr(NovaVersaoProcessoDialog, "_blink_tick")
    assert hasattr(NovaVersaoProcessoDialog, "closeEvent")
