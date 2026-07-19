"""Checks for the configurable group ordering in the costing piece library."""

from app.ui.widgets.ordem_grupos_biblioteca import ordenar_grupos


def test_ordenar_grupos_usa_ordem_do_utilizador() -> None:
    assert ordenar_grupos(
        ["PORTAS", "COSTAS", "FUNDOS"],
        {"COSTAS": 1, "FUNDOS": 2, "PORTAS": 3},
    ) == ["COSTAS", "FUNDOS", "PORTAS"]


def test_dialog_expoe_coluna_de_ordem_por_grupo() -> None:
    from app.ui.dialogs.preferencias_biblioteca_pecas_dialog import (
        PreferenciasBibliotecaPecasDialog,
    )

    source = __import__("inspect").getsource(PreferenciasBibliotecaPecasDialog)
    assert "Ordem do grupo" in source
    assert "QSpinBox" in source
    assert "guardar_ordens_grupos" in source


def test_custeio_aplica_ordem_dos_grupos() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = __import__("inspect").getsource(OrcamentoItemCusteioPage._preencher_biblioteca)
    assert "ordenar_grupos" in source
