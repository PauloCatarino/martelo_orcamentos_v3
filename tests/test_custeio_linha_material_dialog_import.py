"""Import checks for the cost line material dialog."""

from __future__ import annotations

import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.custeio_linha_material_dialog import CusteioLinhaMaterialDialog

    assert CusteioLinhaMaterialDialog is not None


def test_dialog_has_actions() -> None:
    from app.ui.dialogs.custeio_linha_material_dialog import CusteioLinhaMaterialDialog

    for method in ("get_data", "set_error", "_validate_and_accept"):
        assert hasattr(CusteioLinhaMaterialDialog, method)


def test_dialog_get_data_has_material_fields() -> None:
    from app.ui.dialogs.custeio_linha_material_dialog import CusteioLinhaMaterialDialog

    source = inspect.getsource(CusteioLinhaMaterialDialog.get_data)

    for field in (
        "ref_le",
        "descricao_no_orcamento",
        "unidade",
        "preco_liquido",
        "desperdicio_percentagem",
        "tipo_materia_prima",
        "familia_materia_prima",
        "coresp_orla_0_4",
        "coresp_orla_1_0",
        "comp_mp",
        "larg_mp",
        "esp_mp",
    ):
        assert field in source

    assert "_validar_dados" in source
    validar = inspect.getsource(CusteioLinhaMaterialDialog._validar_dados)
    assert "unidade_custo_valida" in validar
    assert "validar_decimal" in validar
