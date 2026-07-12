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


def test_componente_dialog_uses_regra_quantidade_options() -> None:
    from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog

    source_names = DefPecaComponenteDialog.__init__.__code__.co_names
    assert "get_regra_quantidade_options" in source_names

    get_data_source = inspect.getsource(DefPecaComponenteDialog.get_data)
    assert "regra_quantidade_input.currentData" in get_data_source


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
        "formula_comp",
        "formula_larg",
        "formula_esp",
    }
    assert expected <= field_names


def test_componente_dialog_tem_combo_regra_quantidade() -> None:
    from app.ui.dialogs.def_peca_componente_dialog import (
        TOOLTIP_REGRA_QUANTIDADE,
        DefPecaComponenteDialog,
        DefPecaComponenteDialogData,
    )

    field_names = {
        field.name for field in dataclasses.fields(DefPecaComponenteDialogData)
    }
    assert "def_regra_quantidade_id" in field_names

    signature = inspect.signature(DefPecaComponenteDialog)
    assert "regras_disponiveis" in signature.parameters

    init_source = inspect.getsource(DefPecaComponenteDialog.__init__)
    assert "def_regra_quantidade_input" in init_source
    assert "— sem regra —" in init_source

    get_data_source = inspect.getsource(DefPecaComponenteDialog.get_data)
    assert "def_regra_quantidade_input.currentData" in get_data_source

    # The tooltip documents the rule variables.
    for token in ("COMP", "LARG", "ESP", "QT_PAI"):
        assert token in TOOLTIP_REGRA_QUANTIDADE


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


def test_componente_dialog_tem_tooltips_de_configuracao() -> None:
    """G1: every configuration field explains its effect on the costing."""
    from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog

    init = inspect.getsource(DefPecaComponenteDialog.__init__)

    for widget in (
        "tipo_componente_input",
        "descricao_input",
        "quantidade_input",
        "regra_quantidade_input",
        "zona_aplicacao_input",
        "dimensao_referencia_input",
        "numero_topos_input",
        "modo_quantidade_input",
        "prioridade_valueset_input",
        "obrigatorio_input",
        "ativo_input",
    ):
        assert f"self.{widget}.setToolTip(" in init


def test_componente_dialog_tem_seletor_de_referencia() -> None:
    from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog

    assert hasattr(DefPecaComponenteDialog, "selecionar_referencia")

    init = inspect.getsource(DefPecaComponenteDialog.__init__)
    assert "Selecionar..." in init
    assert "selecionar_referencia" in init

    source = inspect.getsource(DefPecaComponenteDialog.selecionar_referencia)
    # Picks from the available DefPeca references and fills the reference field;
    # manual typing stays available as a fallback (referencia_input is a QLineEdit).
    assert "QInputDialog" in source
    assert "_pecas_disponiveis" in source
    assert "referencia_input.setText" in source

    toggle = inspect.getsource(DefPecaComponenteDialog._update_tipo_fields)
    assert "referencia_row" in toggle
