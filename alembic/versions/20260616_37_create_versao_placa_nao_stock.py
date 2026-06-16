"""Per-version board Não-Stock state (phase 8W.2).

Creates ``orcamento_versao_placa_nao_stock`` so the Não-Stock choice of a board
(identified by ref_le / descricao / esp) persists per version and survives any
costing recompute and line recreation.

Revision ID: 20260616_37
Revises: 20260615_36
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260616_37"
down_revision: str | Sequence[str] | None = "20260615_36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABELA = "orcamento_versao_placa_nao_stock"


def upgrade() -> None:
    """Create the board Não-Stock table."""
    op.create_table(
        _TABELA,
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "orcamento_versao_id",
            sa.BigInteger(),
            sa.ForeignKey("orcamento_versoes.id"),
            nullable=False,
        ),
        sa.Column("ref_le", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("descricao", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("esp", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("nao_stock", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "orcamento_versao_id", "ref_le", "descricao", "esp",
            name="uq_versao_placa_nao_stock",
        ),
    )
    op.create_index(
        "ix_versao_placa_nao_stock_versao",
        _TABELA,
        ["orcamento_versao_id"],
    )


def downgrade() -> None:
    """Drop the board Não-Stock table."""
    op.drop_index("ix_versao_placa_nao_stock_versao", table_name=_TABELA)
    op.drop_table(_TABELA)
