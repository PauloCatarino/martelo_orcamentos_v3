"""Add custo_cnc (CNC area-tier cost) to item cost lines (phase 8S.2).

Revision ID: 20260610_25
Revises: 20260610_24
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260610_25"
down_revision: str | Sequence[str] | None = "20260610_24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add custo_cnc (priced by the machine's area tier)."""
    op.add_column(_TABLE, sa.Column("custo_cnc", sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    """Drop custo_cnc."""
    op.drop_column(_TABLE, "custo_cnc")
