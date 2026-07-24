"""Teste do helper puro do diálogo IA Martelo (sem precisar de QApplication)."""

from __future__ import annotations

from types import SimpleNamespace

from app.ui.dialogs.ia_martelo_dialog import IaMarteloDialog


def test_descricao_obra_formata_a_linha() -> None:
    processo = SimpleNamespace(
        id=7,
        codigo_processo="26.1058_01_01_JF_VIVA",
        nome_cliente="MÓVEIS J.F. VIVA",
        estado="Desenho",
        data_entrega="15-07-2026",
    )

    linha = IaMarteloDialog._descricao_obra(processo)

    assert "26.1058_01_01_JF_VIVA" in linha
    assert "MÓVEIS J.F. VIVA" in linha
    assert "Desenho" in linha
    assert "entrega 15-07-2026" in linha


def test_descricao_obra_sem_entrega() -> None:
    processo = SimpleNamespace(
        codigo_processo="26.0800_01", nome_cliente="X", estado="Producao",
        data_entrega=None,
    )

    linha = IaMarteloDialog._descricao_obra(processo)

    assert "entrega" not in linha
    assert linha.startswith("26.0800_01")
