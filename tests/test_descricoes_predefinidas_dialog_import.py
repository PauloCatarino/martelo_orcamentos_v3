"""Import checks for the predefined-descriptions dialog (phase P6a)."""

from __future__ import annotations


def test_descricoes_predefinidas_dialog_imports() -> None:
    from app.ui.dialogs.descricoes_predefinidas_dialog import (
        DescricoesPredefinidasDialog,
    )

    assert DescricoesPredefinidasDialog is not None


def test_descricoes_predefinidas_dialog_registered_in_package() -> None:
    from app.ui.dialogs import DescricoesPredefinidasDialog

    assert DescricoesPredefinidasDialog is not None
