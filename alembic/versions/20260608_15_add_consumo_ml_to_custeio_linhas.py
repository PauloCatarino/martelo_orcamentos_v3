"""Add linear-metre consumption columns to item cost lines (phase 8K).

Revision ID: 20260608_15
Revises: 20260608_14
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_15"
down_revision: str | Sequence[str] | None = "20260608_14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add consumo_ml_unitario / consumo_ml_total (cost still uses custo_ferragem)."""
    op.add_column(
        _TABLE, sa.Column("consumo_ml_unitario", sa.Numeric(14, 4), nullable=True)
    )
    op.add_column(_TABLE, sa.Column("consumo_ml_total", sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    """Drop the linear-metre consumption columns."""
    op.drop_column(_TABLE, "consumo_ml_total")
    op.drop_column(_TABLE, "consumo_ml_unitario")
