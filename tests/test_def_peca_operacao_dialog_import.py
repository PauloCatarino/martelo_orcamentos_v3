"""Import checks for the piece operation dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_def_peca_operacao_dialog_imports() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import (
        DefPecaOperacaoDialog,
        DefPecaOperacaoDialogData,
    )

    assert DefPecaOperacaoDialog is not None
    assert DefPecaOperacaoDialogData is not None


def test_def_peca_operacao_dialog_accepts_args() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    signature = inspect.signature(DefPecaOperacaoDialog)

    assert "operacoes_disponiveis" in signature.parameters
    assert "ligacao" in signature.parameters
    assert "on_save" in signature.parameters
    assert hasattr(DefPecaOperacaoDialog, "set_error")


def test_def_peca_operacao_dialog_data_fields() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialogData

    field_names = {field.name for field in dataclasses.fields(DefPecaOperacaoDialogData)}

    assert {
        "def_operacao_id",
        "ordem",
        "regra_calculo",
        "quantidade_base",
        "obrigatorio",
        "ativo",
        "observacoes",
    } <= field_names


def test_def_peca_operacao_dialog_uses_regra_operacao_options() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    source_names = DefPecaOperacaoDialog.__init__.__code__.co_names

    assert "get_regra_operacao_options" in source_names
    assert "QComboBox" in source_names


def test_def_peca_operacao_dialog_parses_quantidade() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    source = inspect.getsource(DefPecaOperacaoDialog._parse_quantidade)

    assert "Decimal" in source


def test_def_peca_operacao_dialog_locks_operacao_on_edit() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    source = inspect.getsource(DefPecaOperacaoDialog._load_ligacao)

    assert "setEnabled" in source
