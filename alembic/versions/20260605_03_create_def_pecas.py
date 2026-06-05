"""Create piece definition catalog.

Revision ID: 20260605_03
Revises: 20260605_02
Create Date: 2026-06-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_03"
down_revision: str | Sequence[str] | None = "20260605_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create def_pecas table."""
    op.create_table(
        "def_pecas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=100), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("grupo", sa.String(length=100), nullable=True),
        sa.Column("tipo_peca", sa.String(length=50), nullable=False, server_default="SIMPLES"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_def_pecas"),
        sa.UniqueConstraint("codigo", name="uq_def_pecas_codigo"),
    )
    op.create_index("ix_def_pecas_nome", "def_pecas", ["nome"], unique=False)
    op.create_index("ix_def_pecas_grupo", "def_pecas", ["grupo"], unique=False)
    op.create_index("ix_def_pecas_tipo_peca", "def_pecas", ["tipo_peca"], unique=False)
    op.create_index("ix_def_pecas_ativo", "def_pecas", ["ativo"], unique=False)


def downgrade() -> None:
    """Drop def_pecas table."""
    op.drop_index("ix_def_pecas_ativo", table_name="def_pecas")
    op.drop_index("ix_def_pecas_tipo_peca", table_name="def_pecas")
    op.drop_index("ix_def_pecas_grupo", table_name="def_pecas")
    op.drop_index("ix_def_pecas_nome", table_name="def_pecas")
    op.drop_table("def_pecas")
