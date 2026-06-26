"""Import checks for the CUT-RITE progress dialog."""

from __future__ import annotations

import inspect


def test_cutrite_progress_dialog_uses_expected_controls() -> None:
    from app.ui.dialogs.cutrite_progress_dialog import CutRiteProgressDialog

    source = inspect.getsource(CutRiteProgressDialog)

    assert "Enviar CUT-RITE" in source
    assert "QPlainTextEdit" in source
    assert "setReadOnly(True)" in source
    assert "add_step" in source
    assert "finish" in source
    assert "Fechar" in source
