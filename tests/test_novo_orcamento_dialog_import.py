"""Import checks for the new budget dialog."""

from __future__ import annotations


def test_novo_orcamento_dialog_imports() -> None:
    from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog, NovoOrcamentoDialogData

    assert NovoOrcamentoDialog is not None
    assert NovoOrcamentoDialogData is not None
