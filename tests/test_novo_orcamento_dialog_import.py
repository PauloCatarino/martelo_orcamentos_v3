"""Import checks for the new budget dialog."""

from __future__ import annotations

import inspect


def test_novo_orcamento_dialog_imports() -> None:
    from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog, NovoOrcamentoDialogData

    assert NovoOrcamentoDialog is not None
    assert NovoOrcamentoDialogData is not None


def test_novo_orcamento_dialog_tem_combo_de_margens_iniciais() -> None:
    from app.ui.dialogs.novo_orcamento_dialog import (
        NovoOrcamentoDialog,
        NovoOrcamentoDialogData,
    )

    # The data model defaults to the Standard set.
    campos = inspect.signature(NovoOrcamentoDialogData).parameters
    assert "margens_escolha" in campos
    assert campos["margens_escolha"].default == "STANDARD"
    assert "utilizador_id" in campos
    assert campos["utilizador_id"].default is None

    source = inspect.getsource(NovoOrcamentoDialog.__init__)
    assert "Utilizador" in source
    assert '"Standard"' in source
    assert '"Do cliente"' in source
    assert '"Cliente Final"' in source
    assert "Margens iniciais:" in source

    # The customer/user options are enabled only when a record applies.
    assert hasattr(NovoOrcamentoDialog, "_atualizar_opcao_margens_cliente")
    assert hasattr(NovoOrcamentoDialog, "_carregar_disponibilidade_margens")
    assert hasattr(NovoOrcamentoDialog, "_set_opcao_margens_enabled")
