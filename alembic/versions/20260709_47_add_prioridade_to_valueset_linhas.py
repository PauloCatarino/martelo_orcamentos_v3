"""Add prioridade to the ValueSet line tables (model, budget and item).

The active line with the lowest prioridade (1 = first choice) wins the
automatic choice in costing; NULL means no priority (never chosen first).
Backfill: lines flagged padrao=True become prioridade=1.

Revision ID: 20260709_47
Revises: 20260703_47
Create Date: 2026-07-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260709_47"
down_revision: str | Sequence[str] | None = "20260703_47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "def_valueset_modelo_linhas",
    "orcamento_valueset_linhas",
    "orcamento_item_valueset_linhas",
)


def upgrade() -> None:
    """Add prioridade to each ValueSet line table and backfill from padrao."""
    for table in _TABLES:
        op.add_column(table, sa.Column("prioridade", sa.Integer(), nullable=True))
        op.execute(sa.text(f"UPDATE {table} SET prioridade = 1 WHERE padrao = 1"))


def downgrade() -> None:
    """Drop the prioridade columns."""
    for table in _TABLES:
        op.drop_column(table, "prioridade")
