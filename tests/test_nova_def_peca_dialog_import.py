"""Import checks for the new piece definition dialog."""

from __future__ import annotations


def test_nova_def_peca_dialog_imports() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog, NovaDefPecaDialogData

    assert NovaDefPecaDialog is not None
    assert NovaDefPecaDialogData is not None


def test_nova_def_peca_dialog_uses_peca_type_options() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog

    source_names = NovaDefPecaDialog.__init__.__code__.co_names

    assert "get_peca_type_options" in source_names
    assert "QCheckBox" in source_names
