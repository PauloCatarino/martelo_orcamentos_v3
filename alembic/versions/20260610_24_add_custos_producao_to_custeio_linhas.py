"""Add cut/edging/production costs to item cost lines (phase 8S.1).

Revision ID: 20260610_24
Revises: 20260610_23
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260610_24"
down_revision: str | Sequence[str] | None = "20260610_23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"
_COLS = ("custo_corte", "custo_orlagem", "custo_producao")


def upgrade() -> None:
    """Add cutting/edging production cost columns (STD tariffs)."""
    for col in _COLS:
        op.add_column(_TABLE, sa.Column(col, sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    """Drop the production cost columns."""
    for col in reversed(_COLS):
        op.drop_column(_TABLE, col)
