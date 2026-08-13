"""Import checks for the budget item ValueSet line dialog."""

from __future__ import annotations

import dataclasses
import inspect
import sys


def test_dialog_imports() -> None:
    from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
        OrcamentoItemValuesetLinhaDialog,
    )

    assert OrcamentoItemValuesetLinhaDialog is not None


def test_dialog_data_has_expected_fields() -> None:
    from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
        OrcamentoItemValuesetLinhaDialogData,
    )

    field_names = {
        field.name for field in dataclasses.fields(OrcamentoItemValuesetLinhaDialogData)
    }
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
        "prioridade",
        "ordem",
        "observacoes",
        "ativo",
    } <= field_names


def test_dialog_has_actions() -> None:
    from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
        OrcamentoItemValuesetLinhaDialog,
    )

    for method in (
        "abrir_picker_materia_prima",
        "_preencher_de_materia_prima",
        "_recalcular_preco_liquido",
        "_calcular_preco_liquido",
        "_marcar_editado_se_necessario",
        "get_data",
    ):
        assert hasattr(OrcamentoItemValuesetLinhaDialog, method)

    calcular = inspect.getsource(OrcamentoItemValuesetLinhaDialog._calcular_preco_liquido)
    assert "calcular_preco_liquido" in calcular


def test_dialog_so_bloqueia_chave_em_edicao() -> None:
    from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
        OrcamentoItemValuesetLinhaDialog,
    )

    source = inspect.getsource(OrcamentoItemValuesetLinhaDialog.__init__)

    assert "self.chave_input.setEnabled(not self._is_edit)" in source


def test_dialog_permite_nova_linha_e_gravar_como() -> None:
    from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
        OrcamentoItemValuesetLinhaDialog,
    )

    init_source = inspect.getsource(OrcamentoItemValuesetLinhaDialog.__init__)
    gravar_como = inspect.getsource(OrcamentoItemValuesetLinhaDialog._validate_and_save_as)
    validar = inspect.getsource(OrcamentoItemValuesetLinhaDialog._validate_and_run)

    assert "Nova Linha ValueSet do Item" in init_source
    assert "Gravar como…" in init_source
    assert "self.save_as_button.setVisible(self._is_edit)" in init_source
    assert "codigo_opcao_novo=True" in gravar_como
    assert 'codigo_opcao=""' in validar
    assert 'origem_dados="EDITADO_LOCALMENTE"' in validar
    assert "editado_localmente=True" in validar


def test_nova_linha_item_tem_chave_editavel_e_origem_local(monkeypatch) -> None:
    from PySide6.QtWidgets import QApplication

    from app.ui.dialogs import orcamento_item_valueset_linha_dialog as modulo

    app = QApplication.instance() or QApplication(sys.argv)
    monkeypatch.setattr(
        modulo,
        "carregar_chaves_valueset_combo",
        lambda combo, valor_atual=None: combo.addItem(
            "Material peças simplificadas", "MATERIAL_PECAS_SIMPLES"
        ),
    )
    monkeypatch.setattr(
        modulo,
        "obter_valor_chave_combo",
        lambda _combo: "MATERIAL_PECAS_SIMPLES",
    )
    guardado = []
    dialog = modulo.OrcamentoItemValuesetLinhaDialog(
        on_save=lambda dados: guardado.append(dados) or True
    )
    dialog.nome_opcao_input.setText("MDF local do item")

    assert dialog.chave_input.isEnabled()
    assert not dialog.operacoes_button.isEnabled()
    assert dialog.save_as_button.isHidden()
    dialog._validate_and_accept()

    assert guardado[-1].codigo_opcao == ""
    assert guardado[-1].origem_dados == "EDITADO_LOCALMENTE"
    assert guardado[-1].editado_localmente is True
    dialog.deleteLater()
    app.processEvents()


def test_dialog_picker_marks_materia_prima_local() -> None:
    from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
        OrcamentoItemValuesetLinhaDialog,
    )

    fill = inspect.getsource(OrcamentoItemValuesetLinhaDialog._preencher_de_materia_prima)
    assert "MATERIA_PRIMA" in fill
    assert "setChecked(True)" in fill
    assert "normalize_percentagem_humana" in fill
    # Type/family and orla references copied via the centralized resolvers.
    assert "tipo_materia_prima(materia)" in fill
    assert "familia_materia_prima(materia)" in fill
    assert "coresp_orla_0_4(materia)" in fill
    assert "coresp_orla_1_0(materia)" in fill
    assert 'self.orla_0_4_input.setText("")' not in fill
    assert "desperdicio_percentagem" in fill
    assert 'self.desperdicio_input.setText("")' not in fill


def test_dialog_marks_edited_locally() -> None:
    from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
        OrcamentoItemValuesetLinhaDialog,
    )

    marcar = inspect.getsource(OrcamentoItemValuesetLinhaDialog._marcar_editado_se_necessario)
    assert "EDITADO_LOCALMENTE" in marcar


def test_dialog_uses_materia_prima_picker() -> None:
    from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
        OrcamentoItemValuesetLinhaDialog,
    )

    abrir = inspect.getsource(OrcamentoItemValuesetLinhaDialog.abrir_picker_materia_prima)
    assert "MateriaPrimaPickerDialog" in abrir


def test_dialog_has_operacoes_button() -> None:
    from app.ui.dialogs.orcamento_item_valueset_linha_dialog import (
        OrcamentoItemValuesetLinhaDialog,
    )

    init_source = inspect.getsource(OrcamentoItemValuesetLinhaDialog.__init__)
    abrir = inspect.getsource(OrcamentoItemValuesetLinhaDialog.abrir_operacoes_da_linha)

    assert "Operações da linha…" in init_source
    assert "self.operacoes_button.clicked.connect(self.abrir_operacoes_da_linha)" in init_source
    assert "ValuesetLinhaOperacoesDialog" in abrir
    assert "OrcamentoItemValuesetLinhaOperacaoService" in abrir
