"""Add scope/owner fields to def_valueset_modelos.

Revision ID: 20260607_04
Revises: 20260607_03
Create Date: 2026-06-07
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260607_04"
down_revision: str | Sequence[str] | None = "20260607_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ambito, user_id and visivel_para_todos to def_valueset_modelos."""
    op.add_column(
        "def_valueset_modelos",
        sa.Column(
            "ambito",
            sa.String(length=30),
            nullable=False,
            server_default="UTILIZADOR",
        ),
    )
    op.add_column(
        "def_valueset_modelos",
        sa.Column("user_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "def_valueset_modelos",
        sa.Column(
            "visivel_para_todos",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_index(
        "ix_def_valueset_modelos_user_id",
        "def_valueset_modelos",
        ["user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_def_valueset_modelos_user_id_users",
        "def_valueset_modelos",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drop the scope/owner fields from def_valueset_modelos."""
    op.drop_constraint(
        "fk_def_valueset_modelos_user_id_users",
        "def_valueset_modelos",
        type_="foreignkey",
    )
    op.drop_index("ix_def_valueset_modelos_user_id", table_name="def_valueset_modelos")
    op.drop_column("def_valueset_modelos", "visivel_para_todos")
    op.drop_column("def_valueset_modelos", "user_id")
    op.drop_column("def_valueset_modelos", "ambito")
