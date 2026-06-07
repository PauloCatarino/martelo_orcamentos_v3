"""Add ValueSet keys to def_pecas.

Revision ID: 20260607_01
Revises: 20260606_05
Create Date: 2026-06-07
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260607_01"
down_revision: str | Sequence[str] | None = "20260606_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ValueSet key columns to def_pecas."""
    op.add_column(
        "def_pecas",
        sa.Column("chave_valueset_material", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "def_pecas",
        sa.Column(
            "permite_acabamento",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "def_pecas",
        sa.Column("chave_valueset_acabamento_sup", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "def_pecas",
        sa.Column("chave_valueset_acabamento_inf", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """Drop ValueSet key columns from def_pecas."""
    op.drop_column("def_pecas", "chave_valueset_acabamento_inf")
    op.drop_column("def_pecas", "chave_valueset_acabamento_sup")
    op.drop_column("def_pecas", "permite_acabamento")
    op.drop_column("def_pecas", "chave_valueset_material")
