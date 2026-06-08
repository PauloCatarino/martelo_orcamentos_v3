"""Add real measures (comp/larg/esp) to item cost lines (phase 8G).

Revision ID: 20260608_07
Revises: 20260608_06
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_07"
down_revision: str | Sequence[str] | None = "20260608_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add comp_real, larg_real and esp_real to cost lines."""
    op.add_column(_TABLE, sa.Column("comp_real", sa.Numeric(precision=14, scale=3), nullable=True))
    op.add_column(_TABLE, sa.Column("larg_real", sa.Numeric(precision=14, scale=3), nullable=True))
    op.add_column(_TABLE, sa.Column("esp_real", sa.Numeric(precision=14, scale=3), nullable=True))


def downgrade() -> None:
    """Drop the real measure columns."""
    op.drop_column(_TABLE, "esp_real")
    op.drop_column(_TABLE, "larg_real")
    op.drop_column(_TABLE, "comp_real")
