"""Add custo_montagem_manual to item cost lines (phase 8S.3).

Revision ID: 20260610_26
Revises: 20260610_25
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260610_26"
down_revision: str | Sequence[str] | None = "20260610_25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add custo_montagem_manual (assembly/manual/packing time cost)."""
    op.add_column(
        _TABLE, sa.Column("custo_montagem_manual", sa.Numeric(14, 4), nullable=True)
    )


def downgrade() -> None:
    """Drop custo_montagem_manual."""
    op.drop_column(_TABLE, "custo_montagem_manual")
