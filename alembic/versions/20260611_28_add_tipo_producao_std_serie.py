"""STD/SERIE production selector (phase 8S.4).

Adds:
- ``tipo_producao_default`` (orcamento_versoes): production type applied to all
  the version items ('STD'/'SERIE'; default 'STD').
- ``tipo_producao`` (orcamento_items): per-item exception (NULL = inherit the
  version default; 'STD'/'SERIE' = exception).
- ``fator_serie`` (item cost lines): optional manual factor that multiplies ONLY
  the line's custo_producao (empty = 1.00).

Revision ID: 20260611_28
Revises: 20260611_27
Create Date: 2026-06-11
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260611_28"
down_revision: str | Sequence[str] | None = "20260611_27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VERSOES = "orcamento_versoes"
_ITEMS = "orcamento_items"
_LINHAS = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add the STD/SERIE selector columns."""
    op.add_column(
        _VERSOES,
        sa.Column(
            "tipo_producao_default",
            sa.String(length=10),
            nullable=False,
            server_default="STD",
        ),
    )
    op.add_column(
        _ITEMS, sa.Column("tipo_producao", sa.String(length=10), nullable=True)
    )
    op.add_column(
        _LINHAS, sa.Column("fator_serie", sa.Numeric(8, 4), nullable=True)
    )


def downgrade() -> None:
    """Drop the STD/SERIE selector columns."""
    op.drop_column(_LINHAS, "fator_serie")
    op.drop_column(_ITEMS, "tipo_producao")
    op.drop_column(_VERSOES, "tipo_producao_default")
