"""Adicionar suplementos globais de placas não existentes em stock."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260818_88"
down_revision: str | Sequence[str] | None = "20260817_87"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orcamento_versao_placa_nao_stock",
        sa.Column("suplemento_ativo", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "orcamento_versao_placa_nao_stock",
        sa.Column("suplemento_ref_le", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "orcamento_versao_placa_nao_stock",
        sa.Column("suplemento_valor_base", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "orcamento_versao_placa_nao_stock",
        sa.Column("suplemento_valor_local", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "orcamento_versao_placa_nao_stock",
        sa.Column(
            "suplemento_editado_localmente",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    # Migração aditiva: valores locais de orçamentos reais não devem ser
    # eliminados automaticamente por um downgrade.
    pass
