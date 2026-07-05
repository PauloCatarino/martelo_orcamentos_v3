"""Import checks for the ValueSet key dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.def_valueset_chave_dialog import (
        DefValuesetChaveDialog,
        DefValuesetChaveDialogData,
    )

    assert DefValuesetChaveDialog is not None
    assert DefValuesetChaveDialogData is not None


def test_dialog_accepts_chave_and_callback() -> None:
    from app.ui.dialogs.def_valueset_chave_dialog import DefValuesetChaveDialog

    signature = inspect.signature(DefValuesetChaveDialog)

    assert "chave" in signature.parameters
    assert "on_save" in signature.parameters
    assert "on_save_as" in signature.parameters
    assert hasattr(DefValuesetChaveDialog, "set_error")


def test_dialog_data_fields() -> None:
    from app.ui.dialogs.def_valueset_chave_dialog import DefValuesetChaveDialogData

    field_names = {field.name for field in dataclasses.fields(DefValuesetChaveDialogData)}

    assert {
        "codigo",
        "nome",
        "descricao",
        "tipo",
        "grupo",
        "sistema",
        "ordem",
        "observacoes",
        "ativo",
    } <= field_names


def test_dialog_tipo_options() -> None:
    from app.ui.dialogs.def_valueset_chave_dialog import TIPO_OPCOES

    assert TIPO_OPCOES == (
        "MATERIAL",
        "FERRAGEM",
        "SISTEMA_CORRER",
        "ILUMINACAO",
        "ORLA",
        "ACABAMENTO",
        "ACESSORIO",
        "OUTRO",
    )


def test_dialog_grupo_options() -> None:
    from app.ui.dialogs.def_valueset_chave_dialog import GRUPO_OPCOES

    assert "MATERIAIS" in GRUPO_OPCOES
    assert "FERRAGENS" in GRUPO_OPCOES
    assert "ACABAMENTOS" in GRUPO_OPCOES


def test_dialog_uses_combos_and_checkboxes() -> None:
    from app.ui.dialogs.def_valueset_chave_dialog import DefValuesetChaveDialog

    source_names = DefValuesetChaveDialog.__init__.__code__.co_names

    assert "QComboBox" in source_names
    assert "QCheckBox" in source_names


def test_dialog_validates_ordem() -> None:
    from app.ui.dialogs.def_valueset_chave_dialog import DefValuesetChaveDialog

    source = inspect.getsource(DefValuesetChaveDialog._parse_ordem)

    assert "int" in source


def test_dialog_warns_for_system_keys() -> None:
    from app.ui.dialogs.def_valueset_chave_dialog import DefValuesetChaveDialog

    source = inspect.getsource(DefValuesetChaveDialog._load_chave)

    assert "sistema" in source


def test_dialog_has_save_as_button_only_for_edit_mode() -> None:
    from app.ui.dialogs.def_valueset_chave_dialog import DefValuesetChaveDialog

    init_source = inspect.getsource(DefValuesetChaveDialog.__init__)
    validate_source = inspect.getsource(DefValuesetChaveDialog._validate_and_save_as)

    assert "addButton" in init_source
    assert '"Gravar como…"' in init_source
    assert "self.save_as_button.setVisible(self._is_edit)" in init_source
    assert "self.save_as_button.clicked.connect(self._validate_and_save_as)" in init_source
    assert "self._validate_and_run(self.on_save_as)" in validate_source
