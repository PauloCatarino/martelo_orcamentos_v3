"""Import checks for the ValueSet model dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.def_valueset_modelo_dialog import (
        DefValuesetModeloDialog,
        DefValuesetModeloDialogData,
    )

    assert DefValuesetModeloDialog is not None
    assert DefValuesetModeloDialogData is not None


def test_dialog_accepts_modelo_and_callback() -> None:
    from app.ui.dialogs.def_valueset_modelo_dialog import DefValuesetModeloDialog

    signature = inspect.signature(DefValuesetModeloDialog)

    assert "modelo" in signature.parameters
    assert "on_save" in signature.parameters
    assert "on_save_as" in signature.parameters
    assert hasattr(DefValuesetModeloDialog, "set_error")


def test_dialog_data_fields() -> None:
    from app.ui.dialogs.def_valueset_modelo_dialog import DefValuesetModeloDialogData

    field_names = {field.name for field in dataclasses.fields(DefValuesetModeloDialogData)}

    assert {
        "codigo",
        "nome",
        "descricao",
        "tipo",
        "ambito",
        "visivel_para_todos",
        "observacoes",
        "ativo",
    } <= field_names


def test_dialog_ambito_options() -> None:
    from app.ui.dialogs.def_valueset_modelo_dialog import AMBITO_OPCOES

    assert AMBITO_OPCOES == ("UTILIZADOR", "GLOBAL")


def test_dialog_tipo_options() -> None:
    from app.ui.dialogs.def_valueset_modelo_dialog import TIPO_OPCOES

    assert "ROUPEIRO" in TIPO_OPCOES
    assert "COZINHA" in TIPO_OPCOES
    assert "GERAL" in TIPO_OPCOES


def test_dialog_syncs_visivel_from_ambito() -> None:
    from app.ui.dialogs.def_valueset_modelo_dialog import DefValuesetModeloDialog

    source = inspect.getsource(DefValuesetModeloDialog._on_ambito_changed)

    assert "GLOBAL" in source
    assert "visivel" in source


def test_dialog_has_save_as_button_only_for_edit_mode() -> None:
    from app.ui.dialogs.def_valueset_modelo_dialog import DefValuesetModeloDialog

    init_source = inspect.getsource(DefValuesetModeloDialog.__init__)
    validate_source = inspect.getsource(DefValuesetModeloDialog._validate_and_save_as)

    assert "addButton" in init_source
    assert '"Gravar como…"' in init_source
    assert "self.save_as_button.setVisible(self._is_edit)" in init_source
    assert "self.save_as_button.clicked.connect(self._validate_and_save_as)" in init_source
    assert "self._validate_and_run(self.on_save_as)" in validate_source
