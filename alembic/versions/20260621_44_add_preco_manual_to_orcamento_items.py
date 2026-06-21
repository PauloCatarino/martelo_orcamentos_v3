"""Add preco_manual to orcamento_items.

Revision ID: 20260621_44
Revises: 20260621_43
Create Date: 2026-06-21
"""
from __future__ import annotations
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260621_44"
down_revision: str | Sequence[str] | None = "20260621_43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orcamento_items",
        sa.Column("preco_manual", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("orcamento_items", "preco_manual")
