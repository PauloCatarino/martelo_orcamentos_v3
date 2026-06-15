"""Global display order for costing lines (phase 8V.3).

Adds ``ordem_visual`` to ``orcamento_item_custeio_linhas``: a global display
order (distinct from the composite-local ``ordem``) used to splice a SEPARADOR
line right below a selected line. Lines without it keep id order (appended at
the end); inserting a separator renumbers the item's active lines.

Revision ID: 20260615_36
Revises: 20260615_35
Create Date: 2026-06-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260615_36"
down_revision: str | Sequence[str] | None = "20260615_35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABELA = "orcamento_item_custeio_linhas"
_COLUNA = "ordem_visual"


def upgrade() -> None:
    """Add the ordem_visual column."""
    op.add_column(_TABELA, sa.Column(_COLUNA, sa.Integer(), nullable=True))


def downgrade() -> None:
    """Drop the ordem_visual column."""
    op.drop_column(_TABELA, _COLUNA)
