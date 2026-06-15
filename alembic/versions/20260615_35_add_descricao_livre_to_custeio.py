"""Free-text note per costing line (phase 8V.1).

Adds ``descricao_livre`` to ``orcamento_item_custeio_linhas``: an informative,
free-text note editable on every line (pieces, hardware, components, division)
that does NOT collide with the piece's own ``descricao`` and is not used in any
calculation.

Revision ID: 20260615_35
Revises: 20260614_34
Create Date: 2026-06-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260615_35"
down_revision: str | Sequence[str] | None = "20260614_34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABELA = "orcamento_item_custeio_linhas"
_COLUNA = "descricao_livre"


def upgrade() -> None:
    """Add the descricao_livre column."""
    op.add_column(
        _TABELA,
        sa.Column(_COLUNA, sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Drop the descricao_livre column."""
    op.drop_column(_TABELA, _COLUNA)
