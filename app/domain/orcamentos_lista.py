"""Pure helpers for the budget list page."""

from __future__ import annotations

from decimal import Decimal


def resumo_lista(orcamentos):
    """Return (count, total_price), ignoring missing prices in the total."""
    total = Decimal("0")
    contagem = 0
    for orcamento in orcamentos or []:
        contagem += 1
        preco = getattr(orcamento, "preco_total", None)
        if preco is not None:
            total += preco

    return contagem, total
