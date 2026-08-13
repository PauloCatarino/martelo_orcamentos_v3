"""Adicionar nota para o cliente aos suplementos de placas."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260819_89"
down_revision: str | Sequence[str] | None = "20260818_88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orcamento_versao_placa_nao_stock",
        sa.Column("suplemento_nota_cliente", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # Migração aditiva: notas comerciais de orçamentos reais não devem
    # ser eliminadas automaticamente por um downgrade.
    pass
