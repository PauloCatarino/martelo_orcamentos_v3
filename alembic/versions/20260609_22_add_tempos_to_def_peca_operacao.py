"""Add time-configuration fields to piece operations (phase 8R.0).

Revision ID: 20260609_22
Revises: 20260609_21
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260609_22"
down_revision: str | Sequence[str] | None = "20260609_21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "def_peca_operacoes"


def upgrade() -> None:
    """Add setup time, per-unit time and the time unit (all nullable, no default)."""
    op.add_column(
        _TABLE, sa.Column("tempo_setup_minutos", sa.Numeric(14, 4), nullable=True)
    )
    op.add_column(
        _TABLE,
        sa.Column("tempo_por_unidade_minutos", sa.Numeric(14, 4), nullable=True),
    )
    op.add_column(_TABLE, sa.Column("unidade_tempo", sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Drop the time-configuration fields."""
    op.drop_column(_TABLE, "unidade_tempo")
    op.drop_column(_TABLE, "tempo_por_unidade_minutos")
    op.drop_column(_TABLE, "tempo_setup_minutos")
