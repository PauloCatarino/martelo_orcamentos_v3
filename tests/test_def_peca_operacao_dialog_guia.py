"""Behavior tests for the G1 guide inside the piece operation dialog."""

from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.regra_operacao_types import FIXA, RASGO_CNC
from app.repositories.def_operacao_repository import DefOperacaoResumo
from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

_app = QApplication.instance() or QApplication([])


def _operacao(id: int, codigo: str, tipo: str, **kw) -> DefOperacaoResumo:
    return DefOperacaoResumo(
        id=id,
        codigo=codigo,
        nome=codigo.title(),
        descricao=None,
        tipo_operacao=tipo,
        unidade_calculo=None,
        tempo_base=None,
        tempo_setup=None,
        custo_hora=kw.get("custo_hora"),
        custo_minimo=None,
        maquina_id=None,
        ativo=True,
        observacoes=None,
        maquina_codigo=kw.get("maquina_codigo"),
        maquina_permite_rasgos=kw.get("permite_rasgos", False),
        maquina_preco_rasgo_ml_std=kw.get("preco_rasgo"),
    )


def _operacoes() -> list[DefOperacaoResumo]:
    return [
        _operacao(1, "CORTE_SEC", "CORTE"),
        _operacao(2, "CNC_RASGO", "CNC", permite_rasgos=True, preco_rasgo=Decimal("2")),
        _operacao(3, "MONTAGEM_STD", "MONTAGEM", custo_hora=Decimal("45")),
    ]


def _selecionar_operacao(dialog: DefPecaOperacaoDialog, operacao_id: int) -> None:
    dialog.operacao_input.setCurrentIndex(dialog.operacao_input.findData(operacao_id))


def test_guia_mostra_tarifa_em_peca_de_painel() -> None:
    dialog = DefPecaOperacaoDialog(_operacoes(), natureza_peca="MATERIAL")
    _selecionar_operacao(dialog, 1)

    assert "perímetro" in dialog.guia_label.text()
    assert dialog.quantidade_base_input.isEnabled()
    assert dialog.tempo_setup_input.isEnabled()


def test_rasgo_desativa_tempos_e_volta_a_ativar_ao_trocar_operacao() -> None:
    dialog = DefPecaOperacaoDialog(_operacoes(), natureza_peca="MATERIAL")

    _selecionar_operacao(dialog, 2)
    assert dialog.regra_calculo_input.currentData() == RASGO_CNC
    assert not dialog.quantidade_base_input.isEnabled()
    assert not dialog.tempo_setup_input.isEnabled()
    assert not dialog.unidade_tempo_input.isEnabled()
    dialog.rasgo_qt_comp_input.setValue(1)
    assert "0,6 ML" in dialog.guia_label.text()

    # Switching away undoes the rule the dialog forced and re-enables times.
    _selecionar_operacao(dialog, 3)
    assert dialog.regra_calculo_input.currentData() == FIXA
    assert dialog.quantidade_base_input.isEnabled()
    assert dialog.tempo_setup_input.isEnabled()


def test_unidade_m2_e_hora_desativam_os_campos_certos() -> None:
    dialog = DefPecaOperacaoDialog(_operacoes(), natureza_peca="MATERIAL")
    _selecionar_operacao(dialog, 3)

    dialog.unidade_tempo_input.setCurrentIndex(
        dialog.unidade_tempo_input.findData("M2")
    )
    assert not dialog.quantidade_base_input.isEnabled()
    assert dialog.tempo_por_unidade_input.isEnabled()

    dialog.unidade_tempo_input.setCurrentIndex(
        dialog.unidade_tempo_input.findData("HORA")
    )
    assert dialog.quantidade_base_input.isEnabled()
    assert not dialog.tempo_por_unidade_input.isEnabled()


def test_exemplo_numerico_segue_o_motor_de_custeio() -> None:
    dialog = DefPecaOperacaoDialog(_operacoes(), natureza_peca="FERRAGEM")
    _selecionar_operacao(dialog, 3)
    dialog.unidade_tempo_input.setCurrentIndex(
        dialog.unidade_tempo_input.findData("FURO")
    )
    dialog.quantidade_base_input.setText("5")
    dialog.tempo_setup_input.setText("2")
    dialog.tempo_por_unidade_input.setText("0,04")

    texto = dialog.guia_label.text()
    assert "4 min" in texto
    assert "3,00 €" in texto


def test_acao_desativar_mostra_explicacao_propria() -> None:
    dialog = DefPecaOperacaoDialog(_operacoes(), mostrar_acao=True)
    dialog.acao_input.setCurrentIndex(dialog.acao_input.findData("DESATIVAR"))

    assert "desativa" in dialog.guia_label.text().lower()
    assert not dialog.quantidade_base_input.isEnabled()
