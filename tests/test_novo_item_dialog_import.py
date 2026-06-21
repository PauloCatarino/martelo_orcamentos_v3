"""Import checks for the new item dialog."""

from __future__ import annotations


def test_novo_item_dialog_imports() -> None:
    from app.ui.dialogs.novo_item_dialog import NovoItemDialog, NovoItemDialogData

    assert NovoItemDialog is not None
    assert NovoItemDialogData is not None


def test_novo_item_dialog_data_tem_preco_manual_default_false() -> None:
    from decimal import Decimal

    from app.ui.dialogs.novo_item_dialog import NovoItemDialogData

    data = NovoItemDialogData(
        codigo=None,
        item="Mesa",
        descricao=None,
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("0"),
    )

    assert data.preco_manual is False
