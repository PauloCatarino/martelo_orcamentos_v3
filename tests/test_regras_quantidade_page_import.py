"""Import checks for the quantity-rules page, dialog and model (phase 8T.5.0)."""

from __future__ import annotations

import inspect


def test_model_imports_and_registered() -> None:
    from app.models import DefRegraQuantidade

    assert DefRegraQuantidade.__tablename__ == "def_regras_quantidade"


def test_regras_quantidade_page_imports() -> None:
    from app.ui.pages.regras_quantidade_page import RegrasQuantidadePage

    assert RegrasQuantidadePage.TABLE_HEADERS == [
        "Código",
        "Nome",
        "Expressão",
        "Descrição/Tooltip",
        "Ativo",
    ]
    for method in ("carregar", "nova_regra", "editar_regra", "alternar_ativo"):
        assert hasattr(RegrasQuantidadePage, method)


def test_regra_quantidade_dialog_imports() -> None:
    from app.ui.dialogs.regra_quantidade_dialog import (
        TOOLTIP_EXPRESSAO,
        RegraQuantidadeDialog,
        RegraQuantidadeDialogData,
    )

    assert RegraQuantidadeDialog is not None
    assert RegraQuantidadeDialogData is not None
    # The tooltip documents the variables and the functions.
    for token in ("COMP", "LARG", "ESP", "QT_PAI", "CEIL", "FLOOR", "MIN", "MAX"):
        assert token in TOOLTIP_EXPRESSAO


def test_configuracoes_page_has_regras_quantidade_button() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    parameters = inspect.signature(ConfiguracoesPage).parameters
    assert "on_open_regras_quantidade" in parameters

    init_source = inspect.getsource(ConfiguracoesPage.__init__)
    assert "Regras de Quantidade" in init_source
    assert "regras_quantidade_button" in init_source


def test_main_window_wires_regras_quantidade() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow)
    assert "RegrasQuantidadePage" in source
    assert "regras_quantidade" in source
    assert "_open_regras_quantidade" in source
