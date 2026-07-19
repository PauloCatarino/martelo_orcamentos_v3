"""Import checks for the raw material picker dialog."""

from __future__ import annotations

import inspect
from types import SimpleNamespace


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


def test_dialog_aceita_filtros_tipo_familia() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    parametros = inspect.signature(MateriaPrimaPickerDialog).parameters
    assert "initial_tipo" in parametros
    assert "initial_familia" in parametros

    for method in (
        "limpar_filtros",
        "_corresponde",
        "_carregar_opcoes_filtros",
        "_definir_filtro_inicial",
    ):
        assert hasattr(MateriaPrimaPickerDialog, method)

    pesquisar = inspect.getsource(MateriaPrimaPickerDialog.pesquisar)
    assert "tipo_filter" in pesquisar
    assert "familia_filter" in pesquisar
    assert "_aplicar_filtros" in pesquisar


def test_dialog_corresponde_tolera_singular_plural() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    corresponde = inspect.getsource(MateriaPrimaPickerDialog._corresponde)
    # Case-insensitive + singular/plural tolerant (ACABAMENTO matches ACABAMENTOS).
    assert "startswith" in corresponde
    assert "upper" in corresponde


def test_dialog_filtra_orlas_no_catalogo_completo() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    materiais = [
        SimpleNamespace(
            ref_le="PL0001",
            tipo_martelo="AGLOMERADO",
            tipo_original_excel=None,
            familia_martelo="PLACAS",
            familia_original_excel=None,
        ),
        SimpleNamespace(
            ref_le="ORL0002",
            tipo_martelo=None,
            tipo_original_excel="ORLA",
            familia_martelo=None,
            familia_original_excel="ORLA",
        ),
    ]

    assert MateriaPrimaPickerDialog._aplicar_filtros(
        materiais, None, "ORLA", True
    ) == [materiais[1]]


def test_dialog_limpar_filtros_usa_catalogo_ativo_completo() -> None:
    from app.ui.dialogs.materia_prima_picker_dialog import MateriaPrimaPickerDialog

    source = inspect.getsource(MateriaPrimaPickerDialog.pesquisar)
    assert "listar_materias_primas_ativas" in source
    assert "_aplicar_filtros" in source


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
