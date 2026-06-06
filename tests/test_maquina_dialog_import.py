"""Import checks for the machine dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_maquina_dialog_imports() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog, MaquinaDialogData

    assert MaquinaDialog is not None
    assert MaquinaDialogData is not None


def test_maquina_dialog_accepts_maquina_and_callback() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog

    signature = inspect.signature(MaquinaDialog)

    assert "maquina" in signature.parameters
    assert "on_save" in signature.parameters
    assert hasattr(MaquinaDialog, "set_error")


def test_maquina_dialog_data_fields() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialogData

    field_names = {field.name for field in dataclasses.fields(MaquinaDialogData)}

    assert {
        "codigo",
        "nome",
        "descricao",
        "tipo",
        "custo_hora",
        "observacoes",
        "ativo",
    } <= field_names


def test_maquina_dialog_tipo_options() -> None:
    from app.ui.dialogs.maquina_dialog import TIPO_OPCOES

    assert TIPO_OPCOES == ("CORTE", "ORLAGEM", "CNC", "MONTAGEM", "MANUAL", "OUTRO")


def test_maquina_dialog_uses_combobox_for_tipo() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog

    source_names = MaquinaDialog.__init__.__code__.co_names

    assert "QComboBox" in source_names


def test_maquina_dialog_parses_custo_hora_as_decimal() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog

    source = inspect.getsource(MaquinaDialog._parse_custo_hora)

    assert "Decimal" in source


def test_maquina_dialog_blocks_codigo_on_edit() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog

    source = inspect.getsource(MaquinaDialog._load_maquina)

    assert "setReadOnly" in source
