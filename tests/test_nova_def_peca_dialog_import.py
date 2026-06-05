"""Import checks for the new piece definition dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_nova_def_peca_dialog_imports() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog, NovaDefPecaDialogData

    assert NovaDefPecaDialog is not None
    assert NovaDefPecaDialogData is not None


def test_nova_def_peca_dialog_uses_peca_type_options() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog

    source_names = NovaDefPecaDialog.__init__.__code__.co_names

    assert "get_peca_type_options" in source_names
    assert "QCheckBox" in source_names


def test_nova_def_peca_dialog_accepts_save_callback() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog

    signature = inspect.signature(NovaDefPecaDialog)

    assert "on_save" in signature.parameters
    assert hasattr(NovaDefPecaDialog, "set_error")


def test_nova_def_peca_dialog_uses_orla_options() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog

    source_names = NovaDefPecaDialog.__init__.__code__.co_names

    assert "get_orla_type_options" in source_names
    assert "QGroupBox" in source_names


def test_nova_def_peca_dialog_data_has_orla_fields() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialogData

    field_names = {field.name for field in dataclasses.fields(NovaDefPecaDialogData)}

    assert {"orla_c1", "orla_c2", "orla_l1", "orla_l2"} <= field_names


def test_nova_def_peca_dialog_previews_orla_code() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog

    assert hasattr(NovaDefPecaDialog, "_update_orla_preview")

    source = inspect.getsource(NovaDefPecaDialog._update_orla_preview)

    assert "format_orla_code" in source


def test_nova_def_peca_dialog_get_data_includes_orlas() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog

    source = inspect.getsource(NovaDefPecaDialog.get_data)

    for field in ("orla_c1", "orla_c2", "orla_l1", "orla_l2"):
        assert field in source
