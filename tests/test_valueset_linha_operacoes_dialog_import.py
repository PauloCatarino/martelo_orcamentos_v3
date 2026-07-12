"""Import checks for the generic ValueSet line operations dialog."""

from __future__ import annotations

import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.valueset_linha_operacoes_dialog import (
        ValuesetLinhaOperacoesDialog,
    )

    assert ValuesetLinhaOperacoesDialog is not None


def test_dialog_headers_and_callables() -> None:
    from app.ui.dialogs.valueset_linha_operacoes_dialog import (
        ValuesetLinhaOperacoesDialog,
    )

    assert ValuesetLinhaOperacoesDialog.OPERACOES_HEADERS == [
        "Ordem",
        "Ação",
        "Operação",
        "Tipo",
        "Máquina",
        "Regra cálculo",
        "Quantidade base",
        "Construção rasgo",
        "Tempo setup",
        "Tempo por unidade",
        "Unidade tempo",
        "Obrigatório",
        "Ativo",
        "Observações",
    ]

    init = inspect.getsource(ValuesetLinhaOperacoesDialog.__init__)
    assert "listar_operacoes" in init
    assert "criar_operacao" in init
    assert "editar_operacao" in init
    assert "alternar_operacao" in init

    nova = inspect.getsource(ValuesetLinhaOperacoesDialog.abrir_nova_operacao)
    assert "DefPecaOperacaoDialog" in nova

    editar = inspect.getsource(ValuesetLinhaOperacoesDialog.abrir_editar_operacao)
    assert "DefPecaOperacaoDialog" in editar
