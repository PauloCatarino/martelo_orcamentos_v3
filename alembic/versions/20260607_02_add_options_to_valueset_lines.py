"""Add option fields to ValueSet line tables.

Revision ID: 20260607_02
Revises: 20260607_01
Create Date: 2026-06-07
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260607_02"
down_revision: str | Sequence[str] | None = "20260607_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# table, context column, old unique name, new unique name
_TABLES = (
    (
        "def_valueset_modelo_linhas",
        "def_valueset_modelo_id",
        "uq_def_valueset_modelo_linhas_modelo_chave",
        "uq_def_valueset_modelo_linhas_modelo_chave_opcao",
    ),
    (
        "orcamento_valueset_linhas",
        "orcamento_versao_id",
        "uq_orcamento_valueset_linhas_versao_chave",
        "uq_orcamento_valueset_linhas_versao_chave_opcao",
    ),
    (
        "orcamento_item_valueset_linhas",
        "orcamento_item_id",
        "uq_orcamento_item_valueset_linhas_item_chave",
        "uq_orcamento_item_valueset_linhas_item_chave_opcao",
    ),
)


def upgrade() -> None:
    """Add option columns and relax the unique constraint to include codigo_opcao."""
    for table, context_column, old_unique, new_unique in _TABLES:
        op.add_column(
            table, sa.Column("codigo_opcao", sa.String(length=100), nullable=True)
        )
        op.add_column(
            table, sa.Column("nome_opcao", sa.String(length=150), nullable=True)
        )
        op.add_column(
            table,
            sa.Column(
                "padrao", sa.Boolean(), nullable=False, server_default=sa.text("0")
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "ordem", sa.Integer(), nullable=False, server_default=sa.text("1")
            ),
        )
        op.drop_constraint(old_unique, table, type_="unique")
        op.create_unique_constraint(
            new_unique, table, [context_column, "chave", "codigo_opcao"]
        )


def downgrade() -> None:
    """Restore the (context, chave) unique constraint and drop option columns."""
    for table, context_column, old_unique, new_unique in _TABLES:
        op.drop_constraint(new_unique, table, type_="unique")
        op.create_unique_constraint(old_unique, table, [context_column, "chave"])
        op.drop_column(table, "ordem")
        op.drop_column(table, "padrao")
        op.drop_column(table, "nome_opcao")
        op.drop_column(table, "codigo_opcao")
