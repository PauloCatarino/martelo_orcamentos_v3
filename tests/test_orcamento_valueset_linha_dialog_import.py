"""Import checks for the budget ValueSet line dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.orcamento_valueset_linha_dialog import OrcamentoValuesetLinhaDialog

    assert OrcamentoValuesetLinhaDialog is not None


def test_dialog_data_has_expected_fields() -> None:
    from app.ui.dialogs.orcamento_valueset_linha_dialog import OrcamentoValuesetLinhaDialogData

    field_names = {field.name for field in dataclasses.fields(OrcamentoValuesetLinhaDialogData)}
    assert {
        "chave",
        "codigo_opcao",
        "nome_opcao",
        "ref_le",
        "descricao_no_orcamento",
        "ref_materia_prima",
        "descricao_materia_prima",
        "valor_texto",
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
        "padrao",
        "ordem",
        "observacoes",
        "ativo",
    } <= field_names


def test_dialog_has_actions() -> None:
    from app.ui.dialogs.orcamento_valueset_linha_dialog import OrcamentoValuesetLinhaDialog

    for method in (
        "abrir_picker_materia_prima",
        "_preencher_de_materia_prima",
        "_recalcular_preco_liquido",
        "_calcular_preco_liquido",
        "_marcar_editado_se_necessario",
        "get_data",
    ):
        assert hasattr(OrcamentoValuesetLinhaDialog, method)


def test_dialog_locks_chave() -> None:
    from app.ui.dialogs.orcamento_valueset_linha_dialog import OrcamentoValuesetLinhaDialog

    source = inspect.getsource(OrcamentoValuesetLinhaDialog.__init__)

    assert "self.chave_input.setEnabled(False)" in source


def test_dialog_picker_marks_materia_prima_local() -> None:
    from app.ui.dialogs.orcamento_valueset_linha_dialog import OrcamentoValuesetLinhaDialog

    fill = inspect.getsource(OrcamentoValuesetLinhaDialog._preencher_de_materia_prima)
    assert "MATERIA_PRIMA" in fill
    assert "setChecked(True)" in fill
    assert "normalize_percentagem_humana" in fill
    # Type/family and orla references copied via the centralized resolvers.
    assert "tipo_materia_prima(materia)" in fill
    assert "familia_materia_prima(materia)" in fill
    assert "coresp_orla_0_4(materia)" in fill
    assert "coresp_orla_1_0(materia)" in fill
    assert 'self.orla_0_4_input.setText("")' not in fill


def test_dialog_marks_edited_locally() -> None:
    from app.ui.dialogs.orcamento_valueset_linha_dialog import OrcamentoValuesetLinhaDialog

    marcar = inspect.getsource(OrcamentoValuesetLinhaDialog._marcar_editado_se_necessario)
    assert "EDITADO_LOCALMENTE" in marcar


def test_dialog_uses_materia_prima_picker() -> None:
    from app.ui.dialogs.orcamento_valueset_linha_dialog import OrcamentoValuesetLinhaDialog

    abrir = inspect.getsource(OrcamentoValuesetLinhaDialog.abrir_picker_materia_prima)
    assert "MateriaPrimaPickerDialog" in abrir
