"""Add desperdicio_percentagem to raw materials (phase 8H).

Revision ID: 20260608_12
Revises: 20260608_11
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_12"
down_revision: str | Sequence[str] | None = "20260608_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "def_materias_primas"


def upgrade() -> None:
    """Add desperdicio_percentagem (DESP column from the Excel)."""
    op.add_column(
        _TABLE, sa.Column("desperdicio_percentagem", sa.Numeric(8, 4), nullable=True)
    )


def downgrade() -> None:
    """Drop desperdicio_percentagem."""
    op.drop_column(_TABLE, "desperdicio_percentagem")
