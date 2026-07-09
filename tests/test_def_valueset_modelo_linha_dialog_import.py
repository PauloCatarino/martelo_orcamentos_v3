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
    assert "on_save_as" in signature.parameters
    assert hasattr(DefValuesetModeloLinhaDialog, "set_error")


def test_dialog_has_save_as_button_only_for_edit_mode() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog

    init_source = inspect.getsource(DefValuesetModeloLinhaDialog.__init__)
    validate_source = inspect.getsource(DefValuesetModeloLinhaDialog._validate_and_save_as)

    assert "addButton" in init_source
    assert '"Gravar como…"' in init_source
    assert "self.save_as_button.setVisible(self._is_edit)" in init_source
    assert "self.save_as_button.clicked.connect(self._validate_and_save_as)" in init_source
    assert "self._validate_and_run(self.on_save_as)" in validate_source


def test_dialog_has_operacoes_button_only_for_existing_line() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog

    init_source = inspect.getsource(DefValuesetModeloLinhaDialog.__init__)
    abrir = inspect.getsource(DefValuesetModeloLinhaDialog.abrir_operacoes_da_linha)

    assert "Operações da linha…" in init_source
    assert "self.operacoes_button.setEnabled(self._is_edit)" in init_source
    assert "Grave a linha primeiro" in init_source
    assert "ValuesetLinhaOperacoesDialog" in abrir
    assert "DefValuesetModeloLinhaOperacaoService" in abrir


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
        "prioridade",
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


def test_dialog_copia_snapshot_completo_da_materia() -> None:
    from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog

    fill = inspect.getsource(DefValuesetModeloLinhaDialog._preencher_de_materia_prima)

    # Type/family resolved via the centralized resolvers (fallback to Excel).
    assert "tipo_materia_prima(materia)" in fill
    assert "familia_materia_prima(materia)" in fill
    # Orla references copied from the material (no longer hardcoded empty).
    assert "coresp_orla_0_4(materia)" in fill
    assert "coresp_orla_1_0(materia)" in fill
    assert 'self.orla_0_4_input.setText("")' not in fill
    assert 'self.orla_1_0_input.setText("")' not in fill
    # The basic snapshot fields keep being copied.
    assert "materia.ref_le" in fill
    assert "materia.descricao" in fill
    assert "materia.unidade" in fill
    # Desperdício is copied from the material (no longer hardcoded empty).
    assert "desperdicio_percentagem" in fill
    assert 'self.desperdicio_input.setText("")' not in fill


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
    calcular = inspect.getsource(DefValuesetModeloLinhaDialog._calcular_preco_liquido)
    assert "calcular_preco_liquido" in calcular

    marcar = inspect.getsource(DefValuesetModeloLinhaDialog._marcar_editado_se_necessario)
    assert "EDITADO_LOCALMENTE" in marcar
