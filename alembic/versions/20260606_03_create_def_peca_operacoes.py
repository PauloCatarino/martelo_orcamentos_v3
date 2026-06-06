"""Create piece operation links.

Revision ID: 20260606_03
Revises: 20260606_02
Create Date: 2026-06-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260606_03"
down_revision: str | Sequence[str] | None = "20260606_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create def_peca_operacoes table."""
    op.create_table(
        "def_peca_operacoes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("def_peca_id", sa.BigInteger(), nullable=False),
        sa.Column("def_operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("regra_calculo", sa.String(length=100), nullable=True),
        sa.Column("quantidade_base", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("obrigatorio", sa.Boolean(), nullable=False, server_default=sa.text("1")),
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
            ["def_peca_id"],
            ["def_pecas.id"],
            name="fk_def_peca_operacoes_def_peca_id_def_pecas",
        ),
        sa.ForeignKeyConstraint(
            ["def_operacao_id"],
            ["def_operacoes.id"],
            name="fk_def_peca_operacoes_def_operacao_id_def_operacoes",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_def_peca_operacoes"),
        sa.UniqueConstraint(
            "def_peca_id",
            "def_operacao_id",
            name="uq_def_peca_operacoes_peca_operacao",
        ),
    )
    op.create_index(
        "ix_def_peca_operacoes_def_peca_id",
        "def_peca_operacoes",
        ["def_peca_id"],
        unique=False,
    )
    op.create_index(
        "ix_def_peca_operacoes_def_operacao_id",
        "def_peca_operacoes",
        ["def_operacao_id"],
        unique=False,
    )
    op.create_index(
        "ix_def_peca_operacoes_ativo",
        "def_peca_operacoes",
        ["ativo"],
        unique=False,
    )


def downgrade() -> None:
    """Drop def_peca_operacoes table."""
    op.drop_index("ix_def_peca_operacoes_ativo", table_name="def_peca_operacoes")
    op.drop_index("ix_def_peca_operacoes_def_operacao_id", table_name="def_peca_operacoes")
    op.drop_index("ix_def_peca_operacoes_def_peca_id", table_name="def_peca_operacoes")
    op.drop_table("def_peca_operacoes")
