"""Import checks for the ValueSet -> costing propagation dialog."""

from __future__ import annotations

import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.propagar_valueset_custeio_dialog import (
        PropagarValuesetCusteioDialog,
    )

    assert PropagarValuesetCusteioDialog is not None


def test_dialog_headers() -> None:
    from app.ui.dialogs.propagar_valueset_custeio_dialog import (
        PropagarValuesetCusteioDialog,
    )

    headers = PropagarValuesetCusteioDialog.TABLE_HEADERS
    for column in (
        "Atualizar?",
        "ID linha",
        "Tipo linha",
        "Chave ValueSet",
        "Material editado localmente",
        "Ref LE atual",
        "Ref LE ValueSet",
        "PLIQ atual",
        "PLIQ ValueSet",
        "Comp MP atual",
        "Comp MP ValueSet",
        "Esp MP atual",
        "Esp MP ValueSet",
    ):
        assert column in headers


def test_dialog_has_actions() -> None:
    from app.ui.dialogs.propagar_valueset_custeio_dialog import (
        PropagarValuesetCusteioDialog,
    )

    for method in ("_preencher", "_atualizar_selecionadas"):
        assert hasattr(PropagarValuesetCusteioDialog, method)

    source = inspect.getsource(PropagarValuesetCusteioDialog._atualizar_selecionadas)
    assert "selected_ids" in source
