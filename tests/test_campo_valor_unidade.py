"""Tests for the value-with-unit line edit widget."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from app.ui.widgets.campo_valor_unidade import CampoValorComUnidade

_app = QApplication.instance() or QApplication([])


def test_mostra_unidade_e_reserva_margem() -> None:
    campo = CampoValorComUnidade("€")
    campo.setText("8.62")

    assert campo.text() == "8.62"
    assert campo.isReadOnly() is False
    # A right text margin is reserved so the value does not overlap the unit.
    assert campo.textMargins().right() > 0


def test_definir_unidade_vazia_nao_reserva_margem() -> None:
    campo = CampoValorComUnidade("")

    assert campo.textMargins().right() == 0


def test_marcar_como_resultado_protege_o_campo() -> None:
    campo = CampoValorComUnidade("€")
    campo.marcar_como_resultado("Preço líquido = Preço tabela × ...")
    campo.setText("5.79")

    assert campo.isReadOnly() is True
    assert campo.font().bold() is True
    assert "Preço líquido" in campo.toolTip()
    # setText still works on the protected field (it is computed, not typed).
    assert campo.text() == "5.79"
