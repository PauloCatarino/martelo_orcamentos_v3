"""Import checks for the import ValueSet model dialog."""

from __future__ import annotations

import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog

    assert ImportarValuesetModeloDialog is not None


def test_dialog_headers() -> None:
    from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog

    assert ImportarValuesetModeloDialog.TABLE_HEADERS == [
        "Código",
        "Nome",
        "Tipo",
        "Âmbito",
        "Ativo",
    ]


def test_dialog_has_actions() -> None:
    from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog

    for method in ("_carregar", "_aplicar_filtro", "_importar", "_get_selected"):
        assert hasattr(ImportarValuesetModeloDialog, method)


def test_dialog_uses_service() -> None:
    from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog

    source = inspect.getsource(ImportarValuesetModeloDialog._carregar)

    assert "DefValuesetModeloService" in source
    assert "listar_modelos_ativos" in source
