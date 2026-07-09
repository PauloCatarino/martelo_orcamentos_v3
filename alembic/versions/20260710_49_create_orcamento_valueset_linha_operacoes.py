"""Create operations for budget and item ValueSet lines.

Revision ID: 20260710_49
Revises: 20260709_48
Create Date: 2026-07-10
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260710_49"
down_revision: str | Sequence[str] | None = "20260709_48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create budget and item ValueSet line operation links."""
    op.create_table(
        "orcamento_valueset_linha_operacoes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("orcamento_valueset_linha_id", sa.BigInteger(), nullable=False),
        sa.Column("def_operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("ordem", sa.Integer(), server_default="1", nullable=False),
        sa.Column("regra_calculo", sa.String(length=100), nullable=True),
        sa.Column("quantidade_base", sa.Numeric(14, 4), nullable=True),
        sa.Column("tempo_setup_minutos", sa.Numeric(14, 4), nullable=True),
        sa.Column("tempo_por_unidade_minutos", sa.Numeric(14, 4), nullable=True),
        sa.Column("unidade_tempo", sa.String(length=50), nullable=True),
        sa.Column("obrigatorio", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["def_operacao_id"],
            ["def_operacoes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["orcamento_valueset_linha_id"],
            ["orcamento_valueset_linhas.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "orcamento_valueset_linha_id",
            "def_operacao_id",
            name="uq_orcamento_valueset_linha_operacoes_linha_operacao",
        ),
    )
    op.create_index(
        "ix_orcamento_valueset_linha_operacoes_linha",
        "orcamento_valueset_linha_operacoes",
        ["orcamento_valueset_linha_id"],
    )
    op.create_index(
        "ix_orcamento_valueset_linha_operacoes_operacao",
        "orcamento_valueset_linha_operacoes",
        ["def_operacao_id"],
    )
    op.create_index(
        "ix_orcamento_valueset_linha_operacoes_ativo",
        "orcamento_valueset_linha_operacoes",
        ["ativo"],
    )

    op.create_table(
        "orcamento_item_valueset_linha_operacoes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("orcamento_item_valueset_linha_id", sa.BigInteger(), nullable=False),
        sa.Column("def_operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("ordem", sa.Integer(), server_default="1", nullable=False),
        sa.Column("regra_calculo", sa.String(length=100), nullable=True),
        sa.Column("quantidade_base", sa.Numeric(14, 4), nullable=True),
        sa.Column("tempo_setup_minutos", sa.Numeric(14, 4), nullable=True),
        sa.Column("tempo_por_unidade_minutos", sa.Numeric(14, 4), nullable=True),
        sa.Column("unidade_tempo", sa.String(length=50), nullable=True),
        sa.Column("obrigatorio", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["def_operacao_id"],
            ["def_operacoes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["orcamento_item_valueset_linha_id"],
            ["orcamento_item_valueset_linhas.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "orcamento_item_valueset_linha_id",
            "def_operacao_id",
            name="uq_orcamento_item_valueset_linha_operacoes_linha_operacao",
        ),
    )
    op.create_index(
        "ix_orcamento_item_valueset_linha_operacoes_linha",
        "orcamento_item_valueset_linha_operacoes",
        ["orcamento_item_valueset_linha_id"],
    )
    op.create_index(
        "ix_orcamento_item_valueset_linha_operacoes_operacao",
        "orcamento_item_valueset_linha_operacoes",
        ["def_operacao_id"],
    )
    op.create_index(
        "ix_orcamento_item_valueset_linha_operacoes_ativo",
        "orcamento_item_valueset_linha_operacoes",
        ["ativo"],
    )


def downgrade() -> None:
    """Drop budget and item ValueSet line operation links."""
    op.drop_index(
        "ix_orcamento_item_valueset_linha_operacoes_ativo",
        table_name="orcamento_item_valueset_linha_operacoes",
    )
    op.drop_index(
        "ix_orcamento_item_valueset_linha_operacoes_operacao",
        table_name="orcamento_item_valueset_linha_operacoes",
    )
    op.drop_index(
        "ix_orcamento_item_valueset_linha_operacoes_linha",
        table_name="orcamento_item_valueset_linha_operacoes",
    )
    op.drop_table("orcamento_item_valueset_linha_operacoes")

    op.drop_index(
        "ix_orcamento_valueset_linha_operacoes_ativo",
        table_name="orcamento_valueset_linha_operacoes",
    )
    op.drop_index(
        "ix_orcamento_valueset_linha_operacoes_operacao",
        table_name="orcamento_valueset_linha_operacoes",
    )
    op.drop_index(
        "ix_orcamento_valueset_linha_operacoes_linha",
        table_name="orcamento_valueset_linha_operacoes",
    )
    op.drop_table("orcamento_valueset_linha_operacoes")
