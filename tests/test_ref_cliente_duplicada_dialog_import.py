"""Import checks for the duplicate customer reference dialog."""

from __future__ import annotations

import inspect


def test_ref_cliente_duplicada_dialog_imports() -> None:
    from app.ui.dialogs.ref_cliente_duplicada_dialog import RefClienteDuplicadaDialog

    assert RefClienteDuplicadaDialog is not None


def test_ref_cliente_duplicada_dialog_tem_acoes_e_colunas() -> None:
    from app.ui.dialogs.ref_cliente_duplicada_dialog import RefClienteDuplicadaDialog

    assert RefClienteDuplicadaDialog.TABLE_HEADERS == [
        "Ano",
        "N\u00ba Or\u00e7amento",
        "Vers\u00e3o",
        "Cliente",
        "Obra",
        "Estado",
        "Data",
    ]

    source = inspect.getsource(RefClienteDuplicadaDialog.__init__)
    assert "Reabrir selecionado" in source
    assert "Criar novo na mesma" in source
    assert "Cancelar" in source
    assert "Abrir o or\\u00e7amento j\\u00e1 existente." in source
