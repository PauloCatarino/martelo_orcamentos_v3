"""Create budget item modules.

Revision ID: 20260605_02
Revises: 20260605_01
Create Date: 2026-06-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_02"
down_revision: str | Sequence[str] | None = "20260605_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create orcamento_item_modulos table."""
    op.create_table(
        "orcamento_item_modulos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("orcamento_item_id", sa.BigInteger(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("altura", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("largura", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("profundidade", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("quantidade", sa.Numeric(precision=12, scale=3), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["orcamento_item_id"],
            ["orcamento_items.id"],
            name="fk_orcamento_item_modulos_item_id_items",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_orcamento_item_modulos"),
        sa.UniqueConstraint("orcamento_item_id", "ordem", name="uq_orcamento_item_modulos_item_ordem"),
    )
    op.create_index(
        "ix_orcamento_item_modulos_orcamento_item_id",
        "orcamento_item_modulos",
        ["orcamento_item_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop orcamento_item_modulos table."""
    op.drop_index("ix_orcamento_item_modulos_orcamento_item_id", table_name="orcamento_item_modulos")
    op.drop_table("orcamento_item_modulos")
