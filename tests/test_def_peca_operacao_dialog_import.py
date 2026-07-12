"""Import checks for the piece operation dialog."""

from __future__ import annotations

import dataclasses
import inspect
from decimal import Decimal


def test_def_peca_operacao_dialog_imports() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import (
        DefPecaOperacaoDialog,
        DefPecaOperacaoDialogData,
    )

    assert DefPecaOperacaoDialog is not None
    assert DefPecaOperacaoDialogData is not None


def test_def_peca_operacao_dialog_accepts_args() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    signature = inspect.signature(DefPecaOperacaoDialog)

    assert "operacoes_disponiveis" in signature.parameters
    assert "ligacao" in signature.parameters
    assert "on_save" in signature.parameters
    assert hasattr(DefPecaOperacaoDialog, "set_error")


def test_def_peca_operacao_dialog_data_fields() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialogData

    field_names = {field.name for field in dataclasses.fields(DefPecaOperacaoDialogData)}

    assert {
        "def_operacao_id",
        "ordem",
        "regra_calculo",
        "quantidade_base",
        "obrigatorio",
        "ativo",
        "observacoes",
    } <= field_names


def test_def_peca_operacao_dialog_uses_regra_operacao_options() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    source_names = DefPecaOperacaoDialog.__init__.__code__.co_names

    assert "get_regra_operacao_options" in source_names
    assert "QComboBox" in source_names


def test_def_peca_operacao_dialog_parses_decimais() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    source = inspect.getsource(DefPecaOperacaoDialog._parse_decimal_input)

    assert "Decimal" in source


def test_def_peca_operacao_dialog_formata_decimais_sem_zeros_finais() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    dialog = DefPecaOperacaoDialog.__new__(DefPecaOperacaoDialog)

    assert dialog._format_decimal(Decimal("1.0000")) == "1"
    assert dialog._format_decimal(Decimal("0.0500")) == "0.05"
    assert dialog._format_decimal(Decimal("0.8000")) == "0.8"


def test_def_peca_operacao_dialog_tem_campos_de_tempo() -> None:
    import dataclasses

    from app.ui.dialogs.def_peca_operacao_dialog import (
        DefPecaOperacaoDialog,
        DefPecaOperacaoDialogData,
    )

    campos = {field.name for field in dataclasses.fields(DefPecaOperacaoDialogData)}
    assert {
        "tempo_setup_minutos",
        "tempo_por_unidade_minutos",
        "unidade_tempo",
    } <= campos

    init = inspect.getsource(DefPecaOperacaoDialog.__init__)
    assert "Tempo setup (min)" in init
    assert "Tempo por unidade (min)" in init


def test_def_peca_operacao_dialog_unidade_tempo_labels_claros() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import (
        UNIDADE_TEMPO_LABELS,
        UNIDADE_TEMPO_OPCOES,
    )

    # The stored values keep their codes; HORA is now available.
    assert "HORA" in UNIDADE_TEMPO_OPCOES
    assert "PECA" in UNIDADE_TEMPO_OPCOES
    # The visible labels are descriptive for the user.
    assert UNIDADE_TEMPO_LABELS["PECA"] == "Por peça (multiplica pela QT)"
    assert UNIDADE_TEMPO_LABELS["HORA"] == "Por hora (quantidade base em horas)"
    assert UNIDADE_TEMPO_LABELS["OPERACAO"] == "Por operação (fixo, não multiplica pela QT)"
    assert UNIDADE_TEMPO_LABELS["LOTE"] == "Por lote (fixo)"
    # Every stored option has a label.
    assert set(UNIDADE_TEMPO_OPCOES) <= set(UNIDADE_TEMPO_LABELS)


def test_def_peca_operacao_dialog_allows_changing_operacao_on_edit() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    source = inspect.getsource(DefPecaOperacaoDialog._load_ligacao)

    assert "setCurrentIndex" in source
    assert "setEnabled(False)" not in source


def test_def_peca_operacao_dialog_tem_guia_de_configuracao() -> None:
    """G1: the dialog shows the active formula and disables fields per guide."""
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    signature = inspect.signature(DefPecaOperacaoDialog)
    assert "natureza_peca" in signature.parameters

    init = inspect.getsource(DefPecaOperacaoDialog.__init__)
    assert "guia_label" in init
    assert "_tooltips_base_guia" in init

    assert hasattr(DefPecaOperacaoDialog, "_atualizar_guia")
    guia = inspect.getsource(DefPecaOperacaoDialog._atualizar_guia)
    assert "construir_guia_operacao" in guia
    assert "campos_inativos" in guia
    assert "setToolTip" in guia
    # The DESATIVAR variant action keeps its own explanation.
    assert "desativa" in guia.lower()


def test_def_peca_operacao_dialog_guia_recalcula_ao_mudar_campos() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    init = inspect.getsource(DefPecaOperacaoDialog.__init__)
    # Formula panel follows the operation, rule, unit, quantities and times.
    assert init.count("_atualizar_guia") >= 3

    acao = inspect.getsource(DefPecaOperacaoDialog._update_acao_fields)
    assert "_atualizar_guia" in acao
    rasgo = inspect.getsource(DefPecaOperacaoDialog._update_rasgo_fields)
    assert "_atualizar_guia" in rasgo


def test_def_peca_operacao_dialog_tem_tooltips_nos_campos() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    init = inspect.getsource(DefPecaOperacaoDialog.__init__)

    for widget in (
        "operacao_input",
        "ordem_input",
        "regra_calculo_input",
        "rasgo_qt_comp_input",
        "rasgo_qt_larg_input",
        "obrigatorio_input",
        "ativo_input",
        "observacoes_input",
    ):
        assert f"self.{widget}.setToolTip(" in init
