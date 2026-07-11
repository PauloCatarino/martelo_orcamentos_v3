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


def test_nova_def_peca_dialog_uses_controlled_structural_origins() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog

    source = inspect.getsource(NovaDefPecaDialog.__init__)
    assert "get_peca_funcao_options" in source
    assert "Origem estrutural" in source
    assert "setEditable(True)" in source


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


def test_nova_def_peca_dialog_data_has_valueset_fields() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialogData

    field_names = {field.name for field in dataclasses.fields(NovaDefPecaDialogData)}

    assert {
        "chave_valueset_material",
        "permite_acabamento",
        "chave_valueset_acabamento_sup",
        "chave_valueset_acabamento_inf",
    } <= field_names


def test_nova_def_peca_dialog_data_has_sem_material() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialogData

    field_names = {field.name for field in dataclasses.fields(NovaDefPecaDialogData)}

    assert "sem_material" in field_names


def test_nova_def_peca_dialog_sem_material_disables_material_combo() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog

    assert hasattr(NovaDefPecaDialog, "_update_sem_material_enabled")
    init = inspect.getsource(NovaDefPecaDialog.__init__)
    assert "Peça de serviço (sem material)" in init


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


def test_nova_def_peca_dialog_uses_valueset_combo_helper() -> None:
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog

    source_init = inspect.getsource(NovaDefPecaDialog.__init__)
    source_get_data = inspect.getsource(NovaDefPecaDialog.get_data)

    assert "carregar_chaves_valueset_combo" in source_init
    assert "ACABAMENTO" in source_init
    assert "obter_valor_chave_combo" in source_get_data
    assert "chave_valueset_material" in source_get_data
    assert "chave_valueset_acabamento_sup" in source_get_data
    assert "chave_valueset_acabamento_inf" in source_get_data
