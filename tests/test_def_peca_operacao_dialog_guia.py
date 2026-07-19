"""Behavior tests for the G1 guide inside the piece operation dialog."""

from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.metodo_calculo_types import FURACAO, RASGO
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
        maquina_tipo=kw.get("maquina_tipo"),
        maquina_permite_furacao=kw.get("permite_furacao", False),
        maquina_permite_pocket=kw.get("permite_pocket", False),
        maquina_preco_furo_std=kw.get("preco_furo"),
        maquina_preco_ml_std=kw.get("preco_ml"),
        maquina_preco_lado_curto_std=kw.get("preco_lado_curto"),
        maquina_preco_lado_longo_std=kw.get("preco_lado_longo"),
        maquina_limite_lado_mm=kw.get("limite_lado"),
        maquina_custo_setup_peca_std=kw.get("custo_setup_peca"),
    )


def _operacoes() -> list[DefOperacaoResumo]:
    return [
        _operacao(1, "CORTE_SEC", "CORTE"),
        _operacao(
            2,
            "CNC_VERTICAL",
            "CNC",
            maquina_tipo="CNC",
            permite_rasgos=True,
            permite_furacao=True,
            permite_pocket=True,
            preco_rasgo=Decimal("2"),
            preco_furo=Decimal("0.12"),
        ),
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
    dialog.metodo_input.setCurrentIndex(dialog.metodo_input.findData(RASGO))
    assert dialog.metodo_input.currentData() == RASGO
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


# --- G2: panel tariff simulator --------------------------------------------------


def test_simulador_tarifa_corte_decompoe_em_euros() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import SimuladorTarifaPainelDialog

    operacao = _operacao(
        10, "CORTE_SEC", "CORTE",
        preco_ml=Decimal("1.2"), custo_setup_peca=Decimal("0.3"),
    )

    dialog = SimuladorTarifaPainelDialog(bucket="corte", operacao=operacao, escaloes=[])
    # COMP 600 + LARG 400 -> perímetro 2 ML; 2 × 1 × 1,2 + 1 × 0,3 = 2,70 €
    texto = dialog.resultado.text()
    assert "2 ML" in texto
    assert "2,70 €" in texto


def test_simulador_tarifa_orlagem_lista_lados() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import SimuladorTarifaPainelDialog

    operacao = _operacao(
        11, "ORLA_1", "ORLAGEM",
        preco_lado_curto=Decimal("0.5"), preco_lado_longo=Decimal("0.8"),
        limite_lado=Decimal("1500"),
    )

    dialog = SimuladorTarifaPainelDialog(bucket="orlagem", operacao=operacao, escaloes=[])
    # Código 1111, 600/400 mm: 4 lados curtos × 0,5 € = 2,00 €
    texto = dialog.resultado.text()
    assert "C1" in texto and "L2" in texto
    assert "2,00 €" in texto

    dialog.orlas_input.setText("0000")
    assert "custo 0,00 €" in dialog.resultado.text()


def test_simulador_tarifa_cnc_usa_escalao_de_area() -> None:
    from app.repositories.def_maquina_escalao_area_repository import (
        DefMaquinaEscalaoAreaResumo,
    )
    from app.ui.dialogs.def_peca_operacao_dialog import SimuladorTarifaPainelDialog

    escaloes = [
        DefMaquinaEscalaoAreaResumo(
            id=1, def_maquina_id=1, nivel=1, area_max_m2=Decimal("0.25"),
            preco_peca_std=Decimal("1.5"), preco_peca_serie=None, ativo=True,
        ),
        DefMaquinaEscalaoAreaResumo(
            id=2, def_maquina_id=1, nivel=2, area_max_m2=None,
            preco_peca_std=Decimal("2.5"), preco_peca_serie=None, ativo=True,
        ),
    ]
    operacao = _operacao(12, "CNC_STD", "CNC")

    dialog = SimuladorTarifaPainelDialog(bucket="cnc", operacao=operacao, escaloes=escaloes)
    # 600 × 400 = 0,24 m² -> escalão 1 (≤ 0,25) -> 1,5 € × QT 1
    texto = dialog.resultado.text()
    assert "0,24 m²" in texto
    assert "1,50 €" in texto

    dialog.comp_input.setText("1000")
    dialog.larg_input.setText("500")  # 0,5 m² -> escalão 2 sem limite
    assert "2,50 €" in dialog.resultado.text()


def test_simular_abre_tarifa_para_paineis_e_tempo_para_ferragens() -> None:
    import inspect

    source = inspect.getsource(DefPecaOperacaoDialog._abrir_simulador)
    assert "SimuladorTarifaPainelDialog" in source
    assert "classificar_operacao" in source
    assert "FERRAGEM" in source


# --- G3: configuration recipes ----------------------------------------------------


def _aplicar_receita(dialog: DefPecaOperacaoDialog, key: str) -> None:
    dialog.receita_input.setCurrentIndex(dialog.receita_input.findData(key))


def test_receita_furacao_preenche_os_campos_certos() -> None:
    dialog = DefPecaOperacaoDialog(_operacoes(), natureza_peca="FERRAGEM")
    _selecionar_operacao(dialog, 2)

    _aplicar_receita(dialog, "FERRAGEM_FURACAO_CNC")

    assert dialog.metodo_input.currentData() == FURACAO
    assert dialog.quantidade_base_input.text() == "3"
    assert dialog.regra_calculo_input.currentData() == "POR_FURACAO"
    # The combo returns to the placeholder so it can be re-applied later.
    assert dialog.receita_input.currentIndex() == 0
    # The live guide immediately shows the resulting formula.
    assert not dialog.tempo_por_unidade_input.isEnabled()


def test_receita_rasgo_aplica_metodo_na_operacao_cnc_selecionada() -> None:
    dialog = DefPecaOperacaoDialog(_operacoes(), natureza_peca="MATERIAL")
    _selecionar_operacao(dialog, 2)

    _aplicar_receita(dialog, "RASGO_POR_COMPRIMENTO")

    operacao = dialog._operacao_selecionada()
    assert operacao is not None and operacao.codigo == "CNC_VERTICAL"
    assert dialog.metodo_input.currentData() == RASGO
    assert dialog.rasgo_qt_comp_input.value() == 1
    assert dialog.regra_calculo_input.currentData() == RASGO_CNC


def test_receita_rasgo_sem_capacidade_nao_e_mostrada() -> None:
    operacoes = [op for op in _operacoes() if op.codigo != "CNC_VERTICAL"]
    dialog = DefPecaOperacaoDialog(operacoes, natureza_peca="MATERIAL")

    assert dialog.receita_input.findData("RASGO_POR_COMPRIMENTO") == -1


def test_regras_informativas_estao_marcadas_no_dropdown() -> None:
    dialog = DefPecaOperacaoDialog(_operacoes())

    textos = [
        dialog.regra_calculo_input.itemText(i)
        for i in range(dialog.regra_calculo_input.count())
    ]
    informativas = [t for t in textos if "(informativa)" in t]
    # Every rule except 'Rasgo CNC' is documentation only — and now says so.
    assert len(informativas) == len(textos) - 1
    assert not any(
        "(informativa)" in t and "Rasgo CNC" in t for t in textos
    )
