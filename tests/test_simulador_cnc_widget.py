"""Behaviour coverage for the interactive CNC/coating simulator."""

from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.metodo_calculo_types import FURACAO, POCKET, RASGO, REVESTIMENTO
from app.ui.widgets.simulador_cnc_widget import (
    MaquinaSimulacao,
    SimuladorCncWidget,
)

_app = QApplication.instance() or QApplication([])


def _maquina_cnc() -> MaquinaSimulacao:
    return MaquinaSimulacao(
        codigo="CNC_VERTICAL",
        nome="CNC Vertical",
        custo_hora_std=Decimal("60"),
        preco_furo_std=Decimal("0.12"),
        preco_rasgo_ml_std=Decimal("2"),
        permite_furacao=True,
        permite_rasgos=True,
        permite_pocket=True,
    )


def test_tarifas_da_maquina_respeitam_fallback_serie() -> None:
    maquina = _maquina_cnc()

    tarifas = maquina.tarifas(usar_serie=True)

    assert tarifas.preco_furo == Decimal("0.12")
    assert tarifas.preco_rasgo_ml == Decimal("2")
    assert tarifas.permite_furacao is True


def test_widget_adiciona_operacao_compativel_e_mostra_total() -> None:
    widget = SimuladorCncWidget([_maquina_cnc()], mostrar_cenarios=False)

    assert widget.adicionar_operacao("CNC_VERTICAL", FURACAO, furos=3) is True

    assert widget.ops_table.rowCount() == 1
    assert "0,36" in widget.totais_label.text()


def test_widget_recusa_metodo_que_maquina_nao_permite() -> None:
    widget = SimuladorCncWidget([_maquina_cnc()], mostrar_cenarios=False)

    assert widget.adicionar_operacao("CNC_VERTICAL", REVESTIMENTO, faces=2) is False
    assert widget.ops_table.rowCount() == 0


def test_widget_calcula_rasgo_geometrico() -> None:
    widget = SimuladorCncWidget([_maquina_cnc()], mostrar_cenarios=False)
    widget.definir_peca(600, 400, 2)

    assert widget.adicionar_operacao("CNC_VERTICAL", RASGO, n_comp=1, n_larg=0)
    assert "2,40" in widget.totais_label.text()


def test_widget_expoe_pocket_e_calcula_por_tempo_hora() -> None:
    widget = SimuladorCncWidget([_maquina_cnc()], mostrar_cenarios=False)

    assert widget.metodo_input.findData(POCKET) >= 0
    assert widget.adicionar_operacao(
        "CNC_VERTICAL", POCKET, setup=0, min_unidade=4, unidades=1
    )
    assert "4,00" in widget.totais_label.text()
