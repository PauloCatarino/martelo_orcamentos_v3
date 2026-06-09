"""Add orla cost columns to item cost lines (phase 8H).

Revision ID: 20260608_10
Revises: 20260608_09
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_10"
down_revision: str | Sequence[str] | None = "20260608_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add custo_orla_fina/custo_orla_grossa/custo_orlas (ml columns already exist)."""
    op.add_column(_TABLE, sa.Column("custo_orla_fina", sa.Numeric(14, 4), nullable=True))
    op.add_column(_TABLE, sa.Column("custo_orla_grossa", sa.Numeric(14, 4), nullable=True))
    op.add_column(_TABLE, sa.Column("custo_orlas", sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    """Drop the orla cost columns."""
    op.drop_column(_TABLE, "custo_orlas")
    op.drop_column(_TABLE, "custo_orla_grossa")
    op.drop_column(_TABLE, "custo_orla_fina")
