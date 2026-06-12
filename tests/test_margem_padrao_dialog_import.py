"""Import checks for the default-margin dialog."""

from __future__ import annotations


def test_margem_padrao_dialog_imports() -> None:
    from app.ui.dialogs.margem_padrao_dialog import (
        MargemPadraoDialog,
        MargemPadraoDialogData,
    )

    assert MargemPadraoDialog is not None
    assert MargemPadraoDialogData is not None
    assert hasattr(MargemPadraoDialog, "get_data")
