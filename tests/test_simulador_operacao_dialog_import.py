"""Import and calculation checks for the operation simulator dialog."""

from __future__ import annotations

import inspect
from decimal import Decimal


def test_simulador_operacao_dialog_imports() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import (
        SimuladorOperacaoDialog,
        calcular_simulacao_operacao,
    )

    assert SimuladorOperacaoDialog is not None
    assert calcular_simulacao_operacao is not None


def test_def_peca_operacao_dialog_tem_botao_simular() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import DefPecaOperacaoDialog

    init = inspect.getsource(DefPecaOperacaoDialog.__init__)
    abrir = inspect.getsource(DefPecaOperacaoDialog._abrir_simulador)

    assert "Simular cálculo" in init
    assert "SimuladorOperacaoDialog" in abrir
    assert "dialog.exec()" in abrir


def test_simulador_operacao_calcula_tempo_e_custo_por_cenarios() -> None:
    from app.ui.dialogs.def_peca_operacao_dialog import calcular_simulacao_operacao

    parametros = {
        "unidade_tempo": "PECA",
        "quantidade_base": Decimal("1"),
        "tempo_setup_minutos": Decimal("0.05"),
        "tempo_por_unidade_minutos": Decimal("0.8"),
        "area_m2": None,
        "ml": None,
        "custo_hora": Decimal("60"),
    }

    qt2 = calcular_simulacao_operacao(**parametros, qt_total=Decimal("2"))
    qt5 = calcular_simulacao_operacao(**parametros, qt_total=Decimal("5"))

    assert qt2.setup_minutos == Decimal("0.05")
    assert qt2.variavel_minutos == Decimal("1.6")
    assert qt2.tempo_total_minutos == Decimal("1.65")
    assert qt2.custo == Decimal("1.65")
    assert qt5.tempo_total_minutos == Decimal("4.05")
    assert qt5.custo == Decimal("4.05")
