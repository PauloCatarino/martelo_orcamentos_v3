"""Import checks for the composite piece component dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_componente_dialog_imports() -> None:
    from app.ui.dialogs.def_peca_componente_dialog import (
        DefPecaComponenteDialog,
        DefPecaComponenteDialogData,
    )

    assert DefPecaComponenteDialog is not None
    assert DefPecaComponenteDialogData is not None


def test_componente_dialog_uses_componente_type_options() -> None:
    from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog

    source_names = DefPecaComponenteDialog.__init__.__code__.co_names

    assert "get_componente_type_options" in source_names
    assert "QComboBox" in source_names


def test_componente_dialog_accepts_componente_and_callback() -> None:
    from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog

    signature = inspect.signature(DefPecaComponenteDialog)

    assert "pecas_disponiveis" in signature.parameters
    assert "componente" in signature.parameters
    assert "on_save" in signature.parameters
    assert hasattr(DefPecaComponenteDialog, "set_error")


def test_componente_dialog_data_fields() -> None:
    from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialogData

    field_names = {field.name for field in dataclasses.fields(DefPecaComponenteDialogData)}

    expected = {
        "tipo_componente",
        "def_peca_componente_id",
        "referencia_componente",
        "descricao",
        "ordem",
        "quantidade",
        "regra_quantidade",
        "obrigatorio",
        "ativo",
    }
    assert expected <= field_names


def test_componente_dialog_toggles_peca_vs_referencia() -> None:
    from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog

    assert hasattr(DefPecaComponenteDialog, "_update_tipo_fields")

    source = inspect.getsource(DefPecaComponenteDialog._update_tipo_fields)

    assert "PECA" in source
    assert "setVisible" in source


def test_componente_dialog_shows_type_hint() -> None:
    from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog

    init_source = inspect.getsource(DefPecaComponenteDialog.__init__)
    assert "tipo_hint_label" in init_source

    toggle_source = inspect.getsource(DefPecaComponenteDialog._update_tipo_fields)
    assert "setText" in toggle_source
    assert "biblioteca" in toggle_source
    assert "manualmente" in toggle_source


def test_componente_dialog_validates_before_save() -> None:
    from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog

    source = inspect.getsource(DefPecaComponenteDialog._validate_and_accept)

    assert "def_peca_componente_id" in source
    assert "referencia_componente" in source
