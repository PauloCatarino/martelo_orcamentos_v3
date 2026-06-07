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
