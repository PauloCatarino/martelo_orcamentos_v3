"""Add basic production-time columns to item cost lines (phase 8R).

Revision ID: 20260609_21
Revises: 20260609_20
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260609_21"
down_revision: str | Sequence[str] | None = "20260609_20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"
_COLS = ("tempo_corte", "tempo_orlagem", "tempo_cnc", "tempo_montagem", "tempo_setup")


def upgrade() -> None:
    """Add per-stage production times (minutes); no costs are computed yet."""
    for col in _COLS:
        op.add_column(_TABLE, sa.Column(col, sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    """Drop the per-stage production times."""
    for col in reversed(_COLS):
        op.drop_column(_TABLE, col)
