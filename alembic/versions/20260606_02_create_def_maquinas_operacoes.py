"""Create machine and operation catalogs.

Revision ID: 20260606_02
Revises: 20260606_01
Create Date: 2026-06-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260606_02"
down_revision: str | Sequence[str] | None = "20260606_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create def_maquinas and def_operacoes tables."""
    op.create_table(
        "def_maquinas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(length=100), nullable=True),
        sa.Column("custo_hora", sa.Numeric(precision=14, scale=4), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_def_maquinas"),
        sa.UniqueConstraint("codigo", name="uq_def_maquinas_codigo"),
    )
    op.create_index("ix_def_maquinas_tipo", "def_maquinas", ["tipo"], unique=False)
    op.create_index("ix_def_maquinas_ativo", "def_maquinas", ["ativo"], unique=False)

    op.create_table(
        "def_operacoes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("tipo_operacao", sa.String(length=100), nullable=True),
        sa.Column("unidade_calculo", sa.String(length=50), nullable=True),
        sa.Column("tempo_base", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("tempo_setup", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("custo_hora", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("custo_minimo", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("maquina_id", sa.BigInteger(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["maquina_id"],
            ["def_maquinas.id"],
            name="fk_def_operacoes_maquina_id_def_maquinas",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_def_operacoes"),
        sa.UniqueConstraint("codigo", name="uq_def_operacoes_codigo"),
    )
    op.create_index(
        "ix_def_operacoes_tipo_operacao",
        "def_operacoes",
        ["tipo_operacao"],
        unique=False,
    )
    op.create_index(
        "ix_def_operacoes_unidade_calculo",
        "def_operacoes",
        ["unidade_calculo"],
        unique=False,
    )
    op.create_index("ix_def_operacoes_ativo", "def_operacoes", ["ativo"], unique=False)
    op.create_index(
        "ix_def_operacoes_maquina_id",
        "def_operacoes",
        ["maquina_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop def_operacoes and def_maquinas tables."""
    op.drop_index("ix_def_operacoes_maquina_id", table_name="def_operacoes")
    op.drop_index("ix_def_operacoes_ativo", table_name="def_operacoes")
    op.drop_index("ix_def_operacoes_unidade_calculo", table_name="def_operacoes")
    op.drop_index("ix_def_operacoes_tipo_operacao", table_name="def_operacoes")
    op.drop_table("def_operacoes")
    op.drop_index("ix_def_maquinas_ativo", table_name="def_maquinas")
    op.drop_index("ix_def_maquinas_tipo", table_name="def_maquinas")
    op.drop_table("def_maquinas")
