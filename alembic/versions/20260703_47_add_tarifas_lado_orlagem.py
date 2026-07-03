"""Add per-side edging tariffs to machines.

Revision ID: 20260703_47
Revises: 20260623_46
Create Date: 2026-07-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260703_47"
down_revision: str | Sequence[str] | None = "20260623_46"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MAQUINAS = "def_maquinas"
_NOVOS_CAMPOS = (
    "preco_lado_curto_std",
    "preco_lado_curto_serie",
    "preco_lado_longo_std",
    "preco_lado_longo_serie",
    "limite_lado_mm",
)


def upgrade() -> None:
    """Add ORLAGEM tariffs per edged side and the short/long side limit."""
    for campo in _NOVOS_CAMPOS:
        op.add_column(_MAQUINAS, sa.Column(campo, sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    """Drop ORLAGEM per-side tariffs."""
    for campo in reversed(_NOVOS_CAMPOS):
        op.drop_column(_MAQUINAS, campo)
