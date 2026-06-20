"""Widen telefone/telemovel on clientes for PHC free-text values.

Revision ID: 20260618_42
Revises: 20260618_41
Create Date: 2026-06-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260618_42"
down_revision: str | Sequence[str] | None = "20260618_41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "clientes", "telefone",
        existing_type=sa.String(length=50), type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "clientes", "telemovel",
        existing_type=sa.String(length=50), type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "clientes", "telemovel",
        existing_type=sa.String(length=255), type_=sa.String(length=50),
        existing_nullable=True,
    )
    op.alter_column(
        "clientes", "telefone",
        existing_type=sa.String(length=255), type_=sa.String(length=50),
        existing_nullable=True,
    )
