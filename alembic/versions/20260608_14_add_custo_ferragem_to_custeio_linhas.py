"""Add custo_ferragem to item cost lines (phase 8J).

Revision ID: 20260608_14
Revises: 20260608_13
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_14"
down_revision: str | Sequence[str] | None = "20260608_13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add custo_ferragem (UND material/hardware cost per line)."""
    op.add_column(_TABLE, sa.Column("custo_ferragem", sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    """Drop custo_ferragem."""
    op.drop_column(_TABLE, "custo_ferragem")
