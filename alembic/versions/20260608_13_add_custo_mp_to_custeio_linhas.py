"""Add custo_mp to item cost lines (phase 8I).

Revision ID: 20260608_13
Revises: 20260608_12
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_13"
down_revision: str | Sequence[str] | None = "20260608_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add custo_mp (raw material cost per line)."""
    op.add_column(_TABLE, sa.Column("custo_mp", sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    """Drop custo_mp."""
    op.drop_column(_TABLE, "custo_mp")
