"""Import checks for the operation dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_operacao_dialog_imports() -> None:
    from app.ui.dialogs.operacao_dialog import OperacaoDialog, OperacaoDialogData

    assert OperacaoDialog is not None
    assert OperacaoDialogData is not None


def test_operacao_dialog_accepts_maquinas_operacao_and_callback() -> None:
    from app.ui.dialogs.operacao_dialog import OperacaoDialog

    signature = inspect.signature(OperacaoDialog)

    assert "maquinas_disponiveis" in signature.parameters
    assert "operacao" in signature.parameters
    assert "on_save" in signature.parameters
    assert hasattr(OperacaoDialog, "set_error")


def test_operacao_dialog_data_fields() -> None:
    from app.ui.dialogs.operacao_dialog import OperacaoDialogData

    field_names = {field.name for field in dataclasses.fields(OperacaoDialogData)}

    assert {
        "codigo",
        "nome",
        "descricao",
        "tipo_operacao",
        "unidade_calculo",
        "maquina_id",
        "tempo_base",
        "tempo_setup",
        "custo_hora",
        "custo_minimo",
        "observacoes",
        "ativo",
    } <= field_names


def test_operacao_dialog_uses_operacao_type_options() -> None:
    from app.ui.dialogs.operacao_dialog import OperacaoDialog

    source_names = OperacaoDialog.__init__.__code__.co_names

    assert "get_operacao_type_options" in source_names
    assert "QComboBox" in source_names


def test_operacao_dialog_unidade_options() -> None:
    from app.ui.dialogs.operacao_dialog import UNIDADE_OPCOES

    assert UNIDADE_OPCOES == (
        "PECA",
        "ML",
        "M2",
        "HORA",
        "MINUTO",
        "LOTE",
        "SETUP",
        "FIXO",
        "OUTRO",
    )


def test_operacao_dialog_parses_decimals() -> None:
    from app.ui.dialogs.operacao_dialog import OperacaoDialog

    source = inspect.getsource(OperacaoDialog._parse_decimal)

    assert "Decimal" in source


def test_operacao_dialog_blocks_codigo_on_edit() -> None:
    from app.ui.dialogs.operacao_dialog import OperacaoDialog

    source = inspect.getsource(OperacaoDialog._load_operacao)

    assert "setReadOnly" in source
