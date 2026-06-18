"""Add web and info fields to clientes.

Revision ID: 20260618_41
Revises: 20260618_40
Create Date: 2026-06-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260618_41"
down_revision: str | Sequence[str] | None = "20260618_40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add V2-compatible web and info fields to customers."""
    op.add_column(
        "clientes",
        sa.Column("pagina_web", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column("info_1", sa.Text(), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column("info_2", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop V2-compatible web and info fields from customers."""
    op.drop_column("clientes", "info_2")
    op.drop_column("clientes", "info_1")
    op.drop_column("clientes", "pagina_web")
