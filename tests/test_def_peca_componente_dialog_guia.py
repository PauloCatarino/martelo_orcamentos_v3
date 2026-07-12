"""Behavior tests for the associated-component quantity simulator (phase G2)."""

from __future__ import annotations

import os
from decimal import Decimal
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.dialogs.def_peca_componente_dialog import (
    SimuladorQuantidadeAssociadoDialog,
)

_app = QApplication.instance() or QApplication([])


def _regra(expressao: str) -> SimpleNamespace:
    return SimpleNamespace(id=1, codigo="REGRA_TESTE", expressao=expressao)


def test_regra_por_topo_multiplica_pelos_topos() -> None:
    dialog = SimuladorQuantidadeAssociadoDialog(
        regra=_regra("CEIL(MEDIDA_TOPO / 300)"),
        quantidade_fixa=Decimal("1"),
        modo_quantidade="POR_TOPO",
        numero_topos=2,
        dimensao_referencia="MEDIDA_TOPO",
    )

    # LARG 600 -> MEDIDA_TOPO 600 -> CEIL(600/300) = 2 -> × 2 topos = 4
    texto = dialog.resultado.text()
    assert "MEDIDA_TOPO (MEDIDA_TOPO) = 600 mm" in texto
    assert "Resultado da expressão = 2" in texto
    assert "× 2 topo(s) = 4" in texto
    assert "(qt_und) = 4" in texto


def test_dimensao_comp_muda_a_medida_topo() -> None:
    dialog = SimuladorQuantidadeAssociadoDialog(
        regra=_regra("CEIL(MEDIDA_TOPO / 300)"),
        quantidade_fixa=Decimal("1"),
        modo_quantidade="TOTAL",
        numero_topos=0,
        dimensao_referencia="COMP",
    )

    # COMP 2000 -> CEIL(2000/300) = 7
    assert "(qt_und) = 7" in dialog.resultado.text()

    dialog.comp_input.setText("900")
    assert "(qt_und) = 3" in dialog.resultado.text()


def test_sem_regra_usa_quantidade_fixa() -> None:
    dialog = SimuladorQuantidadeAssociadoDialog(
        regra=None,
        quantidade_fixa=Decimal("3"),
        modo_quantidade="TOTAL",
        numero_topos=0,
        dimensao_referencia="COMP",
    )

    texto = dialog.resultado.text()
    assert "Quantidade fixa = 3" in texto
    assert "(qt_und) = 3" in texto


def test_por_topo_sem_topos_pede_correcao() -> None:
    dialog = SimuladorQuantidadeAssociadoDialog(
        regra=None,
        quantidade_fixa=Decimal("1"),
        modo_quantidade="POR_TOPO",
        numero_topos=0,
        dimensao_referencia="COMP",
    )

    assert "exige 1 ou 2 topos" in dialog.resultado.text()


def test_expressao_invalida_mostra_motivo() -> None:
    dialog = SimuladorQuantidadeAssociadoDialog(
        regra=_regra("CEIL(XPTO)"),
        quantidade_fixa=Decimal("1"),
        modo_quantidade="TOTAL",
        numero_topos=0,
        dimensao_referencia="COMP",
    )

    assert "Regra não calculada" in dialog.resultado.text()
    assert "Variável desconhecida" in dialog.resultado.text()
