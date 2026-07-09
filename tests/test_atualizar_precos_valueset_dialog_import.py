"""Import checks for the ValueSet price update dialog."""

from __future__ import annotations

import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.atualizar_precos_valueset_dialog import (
        AtualizarPrecosValuesetDialog,
    )

    assert AtualizarPrecosValuesetDialog is not None


def test_dialog_headers_and_actions() -> None:
    from app.ui.dialogs.atualizar_precos_valueset_dialog import (
        AtualizarPrecosValuesetDialog,
    )

    assert AtualizarPrecosValuesetDialog.TABLE_HEADERS == [
        "✓ Atualizar?",
        "Chave",
        "Opção",
        "Ref LE",
        "Preço tabela (guardado)",
        "Preço tabela (atual MP)",
        "Preço líquido novo",
    ]

    init = inspect.getsource(AtualizarPrecosValuesetDialog.__init__)
    assert "Atualizar também o modelo de origem" in init
    assert "mostrar_atualizar_modelo_origem" in init
    assert "Atualizar selecionadas" in init
    assert "Manter tudo" in init

    preencher = inspect.getsource(AtualizarPrecosValuesetDialog._preencher)
    assert "Qt.CheckState.Checked" in preencher

    atualizar = inspect.getsource(
        AtualizarPrecosValuesetDialog._atualizar_selecionadas
    )
    assert "selected_divergencias" in atualizar
