"""Offscreen tests for the G4 'Copiar configuração de…' combos in the dialogs."""

from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.configuracao_sugestoes import (
    ORIGEM_PECA,
    ConfigAssociadoExistente,
    ConfigOperacaoExistente,
)
from app.repositories.def_operacao_repository import DefOperacaoResumo
from app.repositories.def_peca_repository import DefPecaResumo
from app.ui.dialogs.def_peca_componente_dialog import DefPecaComponenteDialog
from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

_app = QApplication.instance() or QApplication([])


def _operacao(id: int, codigo: str, tipo: str) -> DefOperacaoResumo:
    return DefOperacaoResumo(
        id=id,
        codigo=codigo,
        nome=codigo.title(),
        descricao=None,
        tipo_operacao=tipo,
        unidade_calculo=None,
        tempo_base=None,
        tempo_setup=None,
        custo_hora=None,
        custo_minimo=None,
        maquina_id=None,
        ativo=True,
        observacoes=None,
    )


def _config_furacao(origem_id: int, label: str, def_operacao_id: int = 1):
    return ConfigOperacaoExistente(
        origem_tipo=ORIGEM_PECA,
        origem_id=origem_id,
        origem_label=label,
        def_operacao_id=def_operacao_id,
        regra_calculo="POR_FURACAO",
        quantidade_base=Decimal("3"),
        rasgo_qt_comp=0,
        rasgo_qt_larg=0,
        tempo_setup_minutos=Decimal("0.5"),
        tempo_por_unidade_minutos=Decimal("0.04"),
        unidade_tempo="FURO",
    )


def test_operacao_sugestao_preenche_o_formulario() -> None:
    dialog = DefPecaOperacaoDialog(
        [_operacao(1, "CNC_VERTICAL", "CNC"), _operacao(2, "MONTAGEM_STD", "MONTAGEM")],
        natureza_peca="FERRAGEM",
        configuracoes_existentes=[_config_furacao(50, "Peça DOBRADICA_35")],
    )

    assert dialog.sugestao_input.isEnabled()
    assert dialog.sugestao_input.count() == 2
    assert "DOBRADICA_35" in dialog.sugestao_input.itemText(1)

    dialog.sugestao_input.setCurrentIndex(1)

    assert dialog.quantidade_base_input.text() == "3"
    assert dialog.tempo_setup_input.text() == "0.5"
    assert dialog.tempo_por_unidade_input.text() == "0.04"
    assert dialog.unidade_tempo_input.currentData() == "FURO"
    assert dialog.regra_calculo_input.currentData() == "POR_FURACAO"
    # The combo returns to the placeholder so it can be reused.
    assert dialog.sugestao_input.currentIndex() == 0


def test_operacao_sem_configuracoes_da_operacao_mostra_combo_desativado() -> None:
    dialog = DefPecaOperacaoDialog(
        [_operacao(1, "CNC_VERTICAL", "CNC"), _operacao(2, "MONTAGEM_STD", "MONTAGEM")],
        configuracoes_existentes=[_config_furacao(50, "Peça X", def_operacao_id=2)],
    )

    # Selected operation (id 1) has no existing configurations.
    assert not dialog.sugestao_input.isEnabled()
    assert "sem configurações" in dialog.sugestao_input.itemText(0)

    # Switching to the operation that HAS configurations enables the combo.
    dialog.operacao_input.setCurrentIndex(dialog.operacao_input.findData(2))
    assert dialog.sugestao_input.isEnabled()


def test_operacao_sem_fontes_esconde_a_linha() -> None:
    dialog = DefPecaOperacaoDialog([_operacao(1, "CNC_VERTICAL", "CNC")])

    assert dialog.sugestao_input.isHidden()
    assert dialog.sugestao_label.isHidden()


def _peca(id: int, codigo: str) -> DefPecaResumo:
    return DefPecaResumo(
        id=id,
        codigo=codigo,
        nome=codigo.title(),
        descricao=None,
        grupo=None,
        tipo_peca="SIMPLES",
        ativo=True,
    )


def _config_associado_peca(origem_id: int, label: str, componente_id: int):
    return ConfigAssociadoExistente(
        origem_id=origem_id,
        def_peca_pai_id=origem_id,
        origem_label=label,
        tipo_componente="PECA",
        def_peca_componente_id=componente_id,
        referencia_componente=None,
        quantidade=Decimal("1"),
        def_regra_quantidade_id=None,
        def_regra_quantidade_codigo=None,
        zona_aplicacao="DOIS_TOPOS",
        dimensao_referencia="MEDIDA_TOPO",
        numero_topos=2,
        modo_quantidade="POR_TOPO",
        formula_comp="PAI_COMP",
    )


def test_associado_sugestao_por_peca_componente_preenche() -> None:
    dialog = DefPecaComponenteDialog(
        [_peca(7, "CAVILHA"), _peca(8, "SUPORTE")],
        configuracoes_existentes=[
            _config_associado_peca(100, "Peça PRATELEIRA", componente_id=7)
        ],
    )

    # The first available piece (id 7) is selected by default.
    assert dialog.sugestao_input.isEnabled()
    assert "PRATELEIRA" in dialog.sugestao_input.itemText(1)

    dialog.sugestao_input.setCurrentIndex(1)

    assert dialog.zona_aplicacao_input.currentData() == "DOIS_TOPOS"
    assert dialog.modo_quantidade_input.currentData() == "POR_TOPO"
    assert dialog.numero_topos_input.value() == 2
    assert dialog.formula_comp_input.text() == "PAI_COMP"

    # Another component piece without configurations -> no suggestions.
    dialog.peca_componente_input.setCurrentIndex(
        dialog.peca_componente_input.findData(8)
    )
    assert not dialog.sugestao_input.isEnabled()


def test_associado_sem_fontes_esconde_a_linha() -> None:
    dialog = DefPecaComponenteDialog([_peca(7, "CAVILHA")])

    assert dialog.sugestao_input.isHidden()
    assert dialog.sugestao_label.isHidden()
