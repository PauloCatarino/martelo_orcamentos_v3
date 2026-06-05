"""Create internal raw material catalog.

Revision ID: 20260605_06
Revises: 20260605_05
Create Date: 2026-06-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_06"
down_revision: str | Sequence[str] | None = "20260605_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create def_materias_primas table."""
    op.create_table(
        "def_materias_primas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ref_le", sa.String(length=100), nullable=True),
        sa.Column("referencia_fornecedor", sa.String(length=150), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("tipo_original_excel", sa.String(length=100), nullable=True),
        sa.Column("familia_original_excel", sa.String(length=100), nullable=True),
        sa.Column("tipo_martelo", sa.String(length=100), nullable=True),
        sa.Column("familia_martelo", sa.String(length=100), nullable=True),
        sa.Column("unidade", sa.String(length=30), nullable=True),
        sa.Column("preco_tabela", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("desconto", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("margem", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("preco_liquido", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("comprimento", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("largura", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("espessura", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("fornecedor", sa.String(length=150), nullable=True),
        sa.Column("origem_dados", sa.String(length=50), nullable=False, server_default="EXCEL"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
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
        sa.PrimaryKeyConstraint("id", name="pk_def_materias_primas"),
        sa.UniqueConstraint("ref_le", name="uq_def_materias_primas_ref_le"),
    )
    op.create_index(
        "ix_def_materias_primas_tipo_martelo", "def_materias_primas", ["tipo_martelo"], unique=False
    )
    op.create_index(
        "ix_def_materias_primas_familia_martelo",
        "def_materias_primas",
        ["familia_martelo"],
        unique=False,
    )
    op.create_index(
        "ix_def_materias_primas_tipo_original_excel",
        "def_materias_primas",
        ["tipo_original_excel"],
        unique=False,
    )
    op.create_index(
        "ix_def_materias_primas_familia_original_excel",
        "def_materias_primas",
        ["familia_original_excel"],
        unique=False,
    )
    op.create_index(
        "ix_def_materias_primas_ativo", "def_materias_primas", ["ativo"], unique=False
    )
    op.create_index(
        "ix_def_materias_primas_origem_dados",
        "def_materias_primas",
        ["origem_dados"],
        unique=False,
    )


def downgrade() -> None:
    """Drop def_materias_primas table."""
    op.drop_index("ix_def_materias_primas_origem_dados", table_name="def_materias_primas")
    op.drop_index("ix_def_materias_primas_ativo", table_name="def_materias_primas")
    op.drop_index(
        "ix_def_materias_primas_familia_original_excel", table_name="def_materias_primas"
    )
    op.drop_index("ix_def_materias_primas_tipo_original_excel", table_name="def_materias_primas")
    op.drop_index("ix_def_materias_primas_familia_martelo", table_name="def_materias_primas")
    op.drop_index("ix_def_materias_primas_tipo_martelo", table_name="def_materias_primas")
    op.drop_table("def_materias_primas")
