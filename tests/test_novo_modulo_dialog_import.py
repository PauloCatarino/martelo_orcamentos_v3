"""Import checks for the new module dialog."""

from __future__ import annotations


def test_novo_modulo_dialog_imports() -> None:
    from app.ui.dialogs.novo_modulo_dialog import NovoModuloDialog, NovoModuloDialogData

    assert NovoModuloDialog is not None
    assert NovoModuloDialogData is not None
