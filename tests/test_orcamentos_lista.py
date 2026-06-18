"""Tests for pure budget-list helpers."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.domain.orcamentos_lista import resumo_lista


def test_resumo_lista_conta_e_soma_precos_ignorando_none() -> None:
    orcamentos = [
        SimpleNamespace(preco_total=Decimal("10.50")),
        SimpleNamespace(preco_total=None),
        SimpleNamespace(preco_total=Decimal("2.25")),
    ]

    contagem, total = resumo_lista(orcamentos)

    assert contagem == 3
    assert total == Decimal("12.75")
