"""Adicionar quantidade aos suplementos de placas."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260820_90"
down_revision: str | Sequence[str] | None = "20260819_89"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orcamento_versao_placa_nao_stock",
        sa.Column(
            "suplemento_quantidade",
            sa.Numeric(12, 3),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    # Migração aditiva: quantidades comerciais de orçamentos reais não
    # devem ser eliminadas automaticamente por um downgrade.
    pass
