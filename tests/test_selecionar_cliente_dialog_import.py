"""Import checks for the customer picker dialog."""

from __future__ import annotations

import inspect


def test_selecionar_cliente_dialog_imports() -> None:
    from app.ui.dialogs.selecionar_cliente_dialog import SelecionarClienteDialog

    assert SelecionarClienteDialog is not None
    assert "apenas_phc" in inspect.signature(SelecionarClienteDialog).parameters
