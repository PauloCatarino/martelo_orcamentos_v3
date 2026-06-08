"""Add model-origin fields to item ValueSet lines.

Revision ID: 20260608_04
Revises: 20260608_03
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_04"
down_revision: str | Sequence[str] | None = "20260608_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_valueset_linhas"


def upgrade() -> None:
    """Add origem_modelo_id and origem_modelo_codigo to item ValueSet lines."""
    op.add_column(_TABLE, sa.Column("origem_modelo_id", sa.BigInteger(), nullable=True))
    op.add_column(_TABLE, sa.Column("origem_modelo_codigo", sa.String(length=100), nullable=True))
    op.create_index(
        "ix_oivl_origem_modelo_id",
        _TABLE,
        ["origem_modelo_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_oivl_origem_modelo_def_valueset_modelos",
        _TABLE,
        "def_valueset_modelos",
        ["origem_modelo_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drop the model-origin columns from item ValueSet lines."""
    op.drop_constraint("fk_oivl_origem_modelo_def_valueset_modelos", _TABLE, type_="foreignkey")
    op.drop_index("ix_oivl_origem_modelo_id", table_name=_TABLE)
    op.drop_column(_TABLE, "origem_modelo_codigo")
    op.drop_column(_TABLE, "origem_modelo_id")
