"""Add custo_acabamento to item cost lines (phase 8O).

Revision ID: 20260608_18
Revises: 20260608_17
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_18"
down_revision: str | Sequence[str] | None = "20260608_17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add custo_acabamento (finishing cost per line)."""
    op.add_column(_TABLE, sa.Column("custo_acabamento", sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    """Drop custo_acabamento."""
    op.drop_column(_TABLE, "custo_acabamento")
