"""Import checks for the budget-to-production conversion dialog."""

from __future__ import annotations

import inspect


def test_converter_orcamento_dialog_imports_and_headers() -> None:
    from app.ui.dialogs.converter_orcamento_dialog import ConverterOrcamentoDialog

    assert ConverterOrcamentoDialog.TABLE_HEADERS == [
        "Ano",
        "Nº Orç",
        "Versão",
        "Cliente",
        "Nº Enc PHC",
        "Preço",
        "Pronto?",
    ]


def test_converter_orcamento_dialog_uses_service_validation_and_buttons() -> None:
    from app.ui.dialogs.converter_orcamento_dialog import ConverterOrcamentoDialog

    source = inspect.getsource(ConverterOrcamentoDialog)

    assert "Converter Orçamento" in source
    assert "listar_orcamentos_convertiveis" in source
    assert "validar_conversao" in source
    assert "CampoPesquisa" in source
    assert '"OK"' in source
    assert '"Cancelar"' in source
    assert "setToolTip" in source
