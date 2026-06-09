"""Add production-operation mapping columns to item cost lines (phase 8Q).

Revision ID: 20260609_20
Revises: 20260609_19
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260609_20"
down_revision: str | Sequence[str] | None = "20260609_19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add operacoes / maquina / tipo_producao (text mapping, no times/costs)."""
    op.add_column(_TABLE, sa.Column("operacoes", sa.String(length=500), nullable=True))
    op.add_column(_TABLE, sa.Column("maquina", sa.String(length=255), nullable=True))
    op.add_column(_TABLE, sa.Column("tipo_producao", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Drop the production-operation mapping columns."""
    op.drop_column(_TABLE, "tipo_producao")
    op.drop_column(_TABLE, "maquina")
    op.drop_column(_TABLE, "operacoes")
