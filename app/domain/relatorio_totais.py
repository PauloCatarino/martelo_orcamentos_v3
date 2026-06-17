"""Totais (puros) do relatório de orçamento (fase 8W.4.1).

Movido de :mod:`app.ui.pages.orcamento_relatorios_page` para ser partilhado
entre a página de relatórios e o gerador de PDF, sem dependências de Qt/DB. A
lógica é a mesma da fase 8W.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Default VAT rate (configurable constant; a per-budget setting can come later).
IVA_PADRAO_PCT = Decimal("23")


@dataclass(frozen=True)
class TotaisRelatorio:
    """Footer totals of the budget report items table."""

    total_qt: Decimal
    subtotal: Decimal
    iva_pct: Decimal
    iva: Decimal
    total_geral: Decimal


def calcular_totais_relatorio(items, iva_pct: Decimal = IVA_PADRAO_PCT) -> TotaisRelatorio:
    """Sum the items' quantity and price, then apply VAT (pure/testable)."""
    total_qt = Decimal("0")
    subtotal = Decimal("0")
    for item in items:
        total_qt += item.quantidade or Decimal("0")
        subtotal += item.preco_total or Decimal("0")
    iva = subtotal * iva_pct / Decimal("100")
    return TotaisRelatorio(
        total_qt=total_qt,
        subtotal=subtotal,
        iva_pct=iva_pct,
        iva=iva,
        total_geral=subtotal + iva,
    )
