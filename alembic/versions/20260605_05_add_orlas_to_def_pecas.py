"""Add edge banding fields to piece definitions.

Revision ID: 20260605_05
Revises: 20260605_04
Create Date: 2026-06-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_05"
down_revision: str | Sequence[str] | None = "20260605_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add edge banding fields to def_pecas."""
    op.add_column("def_pecas", sa.Column("orla_c1", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("def_pecas", sa.Column("orla_c2", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("def_pecas", sa.Column("orla_l1", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("def_pecas", sa.Column("orla_l2", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    """Remove edge banding fields from def_pecas."""
    op.drop_column("def_pecas", "orla_l2")
    op.drop_column("def_pecas", "orla_l1")
    op.drop_column("def_pecas", "orla_c2")
    op.drop_column("def_pecas", "orla_c1")
