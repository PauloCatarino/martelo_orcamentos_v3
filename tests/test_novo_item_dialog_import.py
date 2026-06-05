"""Import checks for the new item dialog."""

from __future__ import annotations


def test_novo_item_dialog_imports() -> None:
    from app.ui.dialogs.novo_item_dialog import NovoItemDialog, NovoItemDialogData

    assert NovoItemDialog is not None
    assert NovoItemDialogData is not None
