"""Import checks for the edit piece definition dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_editar_def_peca_dialog_imports() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import (
        EditarDefPecaDialog,
        EditarDefPecaDialogData,
    )

    assert EditarDefPecaDialog is not None
    assert EditarDefPecaDialogData is not None


def test_editar_def_peca_dialog_accepts_peca_and_save_callback() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialog

    signature = inspect.signature(EditarDefPecaDialog)

    assert "peca" in signature.parameters
    assert "on_save" in signature.parameters
    assert hasattr(EditarDefPecaDialog, "set_error")


def test_editar_def_peca_dialog_loads_current_values() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialog

    assert hasattr(EditarDefPecaDialog, "_load_peca")

    source = inspect.getsource(EditarDefPecaDialog._load_peca)

    assert "setText" in source
    assert "_select_combo_data" in source
    assert "setChecked" in source


def test_editar_def_peca_dialog_data_has_all_fields() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialogData

    field_names = {field.name for field in dataclasses.fields(EditarDefPecaDialogData)}

    assert {"orla_c1", "orla_c2", "orla_l1", "orla_l2"} <= field_names
    assert {"codigo", "nome", "descricao", "tipo_peca", "grupo", "ativo"} <= field_names
    assert {
        "chave_valueset_material",
        "permite_acabamento",
        "chave_valueset_acabamento_sup",
        "chave_valueset_acabamento_inf",
    } <= field_names


def test_editar_def_peca_dialog_previews_orla_code() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialog

    assert hasattr(EditarDefPecaDialog, "_update_orla_preview")

    source = inspect.getsource(EditarDefPecaDialog._update_orla_preview)

    assert "format_orla_code" in source


def test_editar_def_peca_dialog_get_data_includes_orlas() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialog

    source = inspect.getsource(EditarDefPecaDialog.get_data)

    for field in ("orla_c1", "orla_c2", "orla_l1", "orla_l2"):
        assert field in source


def test_editar_def_peca_dialog_uses_valueset_combo_helper() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialog

    source_init = inspect.getsource(EditarDefPecaDialog.__init__)
    source_get_data = inspect.getsource(EditarDefPecaDialog.get_data)

    assert "carregar_chaves_valueset_combo" in source_init
    assert "valor_atual" in source_init
    assert "ACABAMENTO" in source_init
    assert "obter_valor_chave_combo" in source_get_data
    assert "chave_valueset_material" in source_get_data
    assert "chave_valueset_acabamento_sup" in source_get_data
    assert "chave_valueset_acabamento_inf" in source_get_data
