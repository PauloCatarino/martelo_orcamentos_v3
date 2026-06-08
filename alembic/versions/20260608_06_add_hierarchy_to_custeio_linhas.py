"""Add parent/level/order hierarchy to item cost lines (phase 8F).

Revision ID: 20260608_06
Revises: 20260608_05
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_06"
down_revision: str | Sequence[str] | None = "20260608_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add linha_pai_id, nivel and ordem to cost lines."""
    op.add_column(_TABLE, sa.Column("linha_pai_id", sa.BigInteger(), nullable=True))
    op.add_column(
        _TABLE,
        sa.Column("nivel", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(_TABLE, sa.Column("ordem", sa.Integer(), nullable=True))
    op.create_index("ix_oicl_linha_pai_id", _TABLE, ["linha_pai_id"], unique=False)
    op.create_foreign_key(
        "fk_oicl_linha_pai_id_self",
        _TABLE,
        _TABLE,
        ["linha_pai_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drop the hierarchy columns."""
    op.drop_constraint("fk_oicl_linha_pai_id_self", _TABLE, type_="foreignkey")
    op.drop_index("ix_oicl_linha_pai_id", table_name=_TABLE)
    op.drop_column(_TABLE, "ordem")
    op.drop_column(_TABLE, "nivel")
    op.drop_column(_TABLE, "linha_pai_id")
