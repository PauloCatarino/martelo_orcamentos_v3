"""Add item type to budget items.

Revision ID: 20260605_01
Revises: 20260604_01
Create Date: 2026-06-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_01"
down_revision: str | Sequence[str] | None = "20260604_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add tipo_item to existing budget items."""
    op.add_column(
        "orcamento_items",
        sa.Column("tipo_item", sa.String(length=50), nullable=False, server_default="OUTRO"),
    )


def downgrade() -> None:
    """Remove tipo_item from budget items."""
    op.drop_column("orcamento_items", "tipo_item")
