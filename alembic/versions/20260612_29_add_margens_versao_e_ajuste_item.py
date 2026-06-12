"""Margins panel and per-item price adjustment (phase 8T.0).

Adds to ``orcamento_versoes`` the budget-level margins (human percentages,
NOT NULL default 0):

- ``margem_lucro_pct``: profit margin;
- ``margem_mp_pct``: raw materials (boards + edges + hardware);
- ``margem_mao_obra_pct``: production (cut/edging/CNC/assembly/manual);
- ``margem_acabamentos_pct``: finishing;
- ``custos_administrativos_pct``: administrative costs.

Adds to ``orcamento_items`` the manual price adjustment in EUR (may be
negative): ``ajuste_eur`` (NOT NULL default 0).

Revision ID: 20260612_29
Revises: 20260611_28
Create Date: 2026-06-12
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260612_29"
down_revision: str | Sequence[str] | None = "20260611_28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VERSOES = "orcamento_versoes"
_ITEMS = "orcamento_items"

_MARGENS_PCT = (
    "margem_lucro_pct",
    "margem_mp_pct",
    "margem_mao_obra_pct",
    "margem_acabamentos_pct",
    "custos_administrativos_pct",
)


def upgrade() -> None:
    """Add the version margins and the item price adjustment."""
    for coluna in _MARGENS_PCT:
        op.add_column(
            _VERSOES,
            sa.Column(coluna, sa.Numeric(8, 4), nullable=False, server_default="0"),
        )

    op.add_column(
        _ITEMS,
        sa.Column("ajuste_eur", sa.Numeric(14, 4), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Drop the version margins and the item price adjustment."""
    op.drop_column(_ITEMS, "ajuste_eur")
    for coluna in reversed(_MARGENS_PCT):
        op.drop_column(_VERSOES, coluna)
