"""Import checks for the raw material picker dialog."""

from __future__ import annotations

import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    assert MateriaPrimaPickerDialog is not None


def test_dialog_headers() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    assert MateriaPrimaPickerDialog.TABLE_HEADERS == [
        "Ref LE",
        "Descrição orçamento",
        "Unidade",
        "Preço tabela",
        "Margem %",
        "Desconto %",
        "Preço líquido",
        "Desp %",
        "Tipo",
        "Família",
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Ativo",
    ]


def test_dialog_has_actions() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    for method in ("pesquisar", "_selecionar", "_get_selected", "_handle_double_click"):
        assert hasattr(MateriaPrimaPickerDialog, method)


def test_dialog_uses_service() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    source = inspect.getsource(MateriaPrimaPickerDialog.pesquisar)

    assert "DefMateriaPrimaService" in source
    assert "pesquisar" in source


def test_dialog_aceita_filtro_familia() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    assert "familia" in inspect.signature(MateriaPrimaPickerDialog).parameters
    assert hasattr(MateriaPrimaPickerDialog, "_pertence_familia")

    pesquisar = inspect.getsource(MateriaPrimaPickerDialog.pesquisar)
    assert "_familia_filtro" in pesquisar

    pertence = inspect.getsource(MateriaPrimaPickerDialog._pertence_familia)
    assert "familia_materia_prima" in pertence


def test_dialog_normaliza_percentagens() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    source = inspect.getsource(MateriaPrimaPickerDialog._preencher)

    assert "normalize_percentagem_humana" in source


def test_dialog_mostra_tipo_familia_e_orlas() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    source = inspect.getsource(MateriaPrimaPickerDialog._preencher)

    # Type/family fall back to the original Excel columns; orlas use the resolver.
    assert "tipo_materia_prima(materia)" in source
    assert "familia_materia_prima(materia)" in source
    assert "coresp_orla_0_4(materia)" in source
    assert "coresp_orla_1_0(materia)" in source
    # Desp % is shown from the imported desperdicio_percentagem.
    assert "desperdicio_percentagem" in source
