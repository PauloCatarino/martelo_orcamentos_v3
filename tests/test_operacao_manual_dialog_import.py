"""Import checks for the manual-operation dialog (phase 8S.3)."""

from __future__ import annotations

import dataclasses
import inspect


def test_operacao_manual_dialog_imports() -> None:
    from app.ui.dialogs.operacao_manual_dialog import (
        OperacaoManualDialog,
        OperacaoManualDialogData,
    )

    campos = {f.name for f in dataclasses.fields(OperacaoManualDialogData)}
    assert {"descricao", "def_maquina_id", "tempo_minutos", "quantidade"} <= campos
    assert hasattr(OperacaoManualDialog, "get_data")


def test_operacao_manual_dialog_campos() -> None:
    from app.ui.dialogs.operacao_manual_dialog import OperacaoManualDialog

    init = inspect.getsource(OperacaoManualDialog.__init__)
    assert "Descrição" in init
    assert "Máquina" in init
    assert " min" in init  # time suffix
    # pre-selects a MANUAL machine by default
    assert "MANUAL" in init
    # the info text mentions one-off CNC jobs
    assert "CNC" in init


def test_operacao_manual_dialog_aviso_custo_hora() -> None:
    from app.ui.dialogs.operacao_manual_dialog import OperacaoManualDialog

    assert hasattr(OperacaoManualDialog, "_atualizar_aviso_custo_hora")
    aviso = inspect.getsource(OperacaoManualDialog._atualizar_aviso_custo_hora)
    assert "custo/hora STD" in aviso
