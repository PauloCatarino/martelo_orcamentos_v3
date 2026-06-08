"""Add local material flags to item cost lines (phase 8G.3).

Revision ID: 20260608_09
Revises: 20260608_08
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_09"
down_revision: str | Sequence[str] | None = "20260608_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add material_editado_localmente and origem_material to cost lines."""
    op.add_column(
        _TABLE,
        sa.Column(
            "material_editado_localmente",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(_TABLE, sa.Column("origem_material", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Drop the local material flags."""
    op.drop_column(_TABLE, "origem_material")
    op.drop_column(_TABLE, "material_editado_localmente")
