"""Add edge (orla) correspondence columns to raw materials (phase 8H).

Revision ID: 20260608_11
Revises: 20260608_10
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_11"
down_revision: str | Sequence[str] | None = "20260608_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "def_materias_primas"


def upgrade() -> None:
    """Add coresp_orla_0_4 / coresp_orla_1_0 to the raw material catalog."""
    op.add_column(_TABLE, sa.Column("coresp_orla_0_4", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("coresp_orla_1_0", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Drop the orla correspondence columns."""
    op.drop_column(_TABLE, "coresp_orla_1_0")
    op.drop_column(_TABLE, "coresp_orla_0_4")
