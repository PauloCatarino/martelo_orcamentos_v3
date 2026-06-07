"""Create configurable ValueSet keys table.

Revision ID: 20260607_03
Revises: 20260607_02
Create Date: 2026-06-07
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260607_03"
down_revision: str | Sequence[str] | None = "20260607_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create def_valueset_chaves table."""
    op.create_table(
        "def_valueset_chaves",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=100), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(length=100), nullable=True),
        sa.Column("grupo", sa.String(length=100), nullable=True),
        sa.Column("sistema", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_def_valueset_chaves"),
        sa.UniqueConstraint("codigo", name="uq_def_valueset_chaves_codigo"),
    )
    op.create_index("ix_def_valueset_chaves_tipo", "def_valueset_chaves", ["tipo"], unique=False)
    op.create_index("ix_def_valueset_chaves_grupo", "def_valueset_chaves", ["grupo"], unique=False)
    op.create_index("ix_def_valueset_chaves_ativo", "def_valueset_chaves", ["ativo"], unique=False)


def downgrade() -> None:
    """Drop def_valueset_chaves table."""
    op.drop_index("ix_def_valueset_chaves_ativo", table_name="def_valueset_chaves")
    op.drop_index("ix_def_valueset_chaves_grupo", table_name="def_valueset_chaves")
    op.drop_index("ix_def_valueset_chaves_tipo", table_name="def_valueset_chaves")
    op.drop_table("def_valueset_chaves")
