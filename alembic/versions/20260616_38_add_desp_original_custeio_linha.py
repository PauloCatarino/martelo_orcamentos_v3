"""Original (material) waste % on cost lines, for whole-board adjustments (8W.2.1).

Adds ``desperdicio_percentagem_original`` to ``orcamento_item_custeio_linhas``:
the material waste % saved before a Não-Stock board recalculates the line waste
to whole-board figures, so it can be restored when the board is unmarked.

Revision ID: 20260616_38
Revises: 20260616_37
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260616_38"
down_revision: str | Sequence[str] | None = "20260616_37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABELA = "orcamento_item_custeio_linhas"
_COLUNA = "desperdicio_percentagem_original"


def upgrade() -> None:
    """Add the original-waste column (nullable)."""
    op.add_column(_TABELA, sa.Column(_COLUNA, sa.Numeric(8, 4), nullable=True))


def downgrade() -> None:
    """Drop the original-waste column."""
    op.drop_column(_TABELA, _COLUNA)
