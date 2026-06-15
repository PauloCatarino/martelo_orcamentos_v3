"""Module thumbnail on costing lines (phase 8U.4).

Adds ``modulo_imagem_path`` to ``orcamento_item_custeio_linhas``: when a saved
module is imported, the path of its image is stored on the first line of the
imported block so the costing table can show a thumbnail (and a zoom tooltip).

Revision ID: 20260614_34
Revises: 20260614_33
Create Date: 2026-06-14
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_34"
down_revision: str | Sequence[str] | None = "20260614_33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABELA = "orcamento_item_custeio_linhas"
_COLUNA = "modulo_imagem_path"


def upgrade() -> None:
    """Add the modulo_imagem_path column."""
    op.add_column(
        _TABELA,
        sa.Column(_COLUNA, sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Drop the modulo_imagem_path column."""
    op.drop_column(_TABELA, _COLUNA)
