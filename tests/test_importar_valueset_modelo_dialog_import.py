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
        "Ativo",
    ]


def test_dialog_has_actions() -> None:
    from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog

    for method in ("_carregar", "_filtrar", "_importar", "_get_selected", "_aba_ativa"):
        assert hasattr(ImportarValuesetModeloDialog, method)


def test_dialog_has_user_and_global_tabs() -> None:
    from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog

    source = inspect.getsource(ImportarValuesetModeloDialog.__init__)

    assert "QTabWidget" in source
    assert '"Utilizador"' in source
    assert '"Global"' in source


def test_dialog_uses_user_and_global_service_methods() -> None:
    from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog

    source = inspect.getsource(ImportarValuesetModeloDialog._carregar)

    assert "DefValuesetModeloService" in source
    assert "listar_modelos_utilizador" in source
    assert "listar_modelos_globais" in source


def test_dialog_requires_selection_message() -> None:
    from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog

    source = inspect.getsource(ImportarValuesetModeloDialog._importar)

    assert "Selecione um modelo." in source
