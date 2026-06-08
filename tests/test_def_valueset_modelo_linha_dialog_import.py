"""Import checks for the ValueSet model line dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import (
        DefValuesetModeloLinhaDialog,
        DefValuesetModeloLinhaDialogData,
    )

    assert DefValuesetModeloLinhaDialog is not None
    assert DefValuesetModeloLinhaDialogData is not None


def test_dialog_accepts_linha_and_callback() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog

    signature = inspect.signature(DefValuesetModeloLinhaDialog)

    assert "linha" in signature.parameters
    assert "on_save" in signature.parameters
    assert hasattr(DefValuesetModeloLinhaDialog, "set_error")


def test_dialog_data_fields() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialogData

    field_names = {
        field.name for field in dataclasses.fields(DefValuesetModeloLinhaDialogData)
    }

    assert {
        "chave",
        "codigo_opcao",
        "nome_opcao",
        "ref_materia_prima",
        "descricao_materia_prima",
        "valor_texto",
        "padrao",
        "ordem",
        "observacoes",
        "ativo",
    } <= field_names


def test_dialog_data_has_snapshot_fields() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialogData

    field_names = {
        field.name for field in dataclasses.fields(DefValuesetModeloLinhaDialogData)
    }

    assert {
        "ref_le",
        "descricao_no_orcamento",
        "preco_tabela",
        "margem_percentagem",
        "desconto_percentagem",
        "preco_liquido",
        "unidade",
        "desperdicio_percentagem",
        "tipo_materia_prima",
        "familia_materia_prima",
        "coresp_orla_0_4",
        "coresp_orla_1_0",
        "comp_mp",
        "larg_mp",
        "esp_mp",
        "origem_dados",
        "editado_localmente",
    } <= field_names


def test_dialog_uses_chave_helper() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog

    source_init = inspect.getsource(DefValuesetModeloLinhaDialog.__init__)
    source_get_data = inspect.getsource(DefValuesetModeloLinhaDialog.get_data)

    assert "carregar_chaves_valueset_combo" in source_init
    assert "obter_valor_chave_combo" in source_get_data


def test_dialog_validates_ordem() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog

    source = inspect.getsource(DefValuesetModeloLinhaDialog._parse_ordem)

    assert "int" in source


def test_dialog_has_materia_prima_picker() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog

    assert hasattr(DefValuesetModeloLinhaDialog, "abrir_picker_materia_prima")
    assert hasattr(DefValuesetModeloLinhaDialog, "_preencher_de_materia_prima")

    abrir = inspect.getsource(DefValuesetModeloLinhaDialog.abrir_picker_materia_prima)
    assert "MateriaPrimaPickerDialog" in abrir

    fill = inspect.getsource(DefValuesetModeloLinhaDialog._preencher_de_materia_prima)
    assert "MATERIA_PRIMA" in fill


def test_dialog_normaliza_recalcula_e_marca_editado() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog

    for method in (
        "_recalcular_preco_liquido",
        "_calcular_preco_liquido",
        "_marcar_editado_se_necessario",
    ):
        assert hasattr(DefValuesetModeloLinhaDialog, method)

    fill = inspect.getsource(DefValuesetModeloLinhaDialog._preencher_de_materia_prima)
    assert "normalize_percentagem_humana" in fill

    marcar = inspect.getsource(DefValuesetModeloLinhaDialog._marcar_editado_se_necessario)
    assert "EDITADO_LOCALMENTE" in marcar
