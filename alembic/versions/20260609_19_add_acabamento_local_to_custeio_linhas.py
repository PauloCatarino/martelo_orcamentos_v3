"""Add local finishing-edit fields to item cost lines (phase 8O.1).

Revision ID: 20260609_19
Revises: 20260608_18
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260609_19"
down_revision: str | Sequence[str] | None = "20260608_18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add the local finishing flag and per-face price/waste snapshots."""
    op.add_column(
        _TABLE,
        sa.Column(
            "acabamento_editado_localmente",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )
    for face in ("sup", "inf"):
        op.add_column(
            _TABLE, sa.Column(f"acabamento_{face}_ref_le", sa.String(100), nullable=True)
        )
        op.add_column(
            _TABLE,
            sa.Column(f"acabamento_{face}_descricao", sa.String(255), nullable=True),
        )
        op.add_column(
            _TABLE, sa.Column(f"acabamento_{face}_unidade", sa.String(50), nullable=True)
        )
        op.add_column(
            _TABLE,
            sa.Column(f"acabamento_{face}_preco_liquido", sa.Numeric(14, 4), nullable=True),
        )
        op.add_column(
            _TABLE,
            sa.Column(
                f"acabamento_{face}_desperdicio_percentagem",
                sa.Numeric(8, 4),
                nullable=True,
            ),
        )


def downgrade() -> None:
    """Drop the local finishing fields."""
    for face in ("inf", "sup"):
        op.drop_column(_TABLE, f"acabamento_{face}_desperdicio_percentagem")
        op.drop_column(_TABLE, f"acabamento_{face}_preco_liquido")
        op.drop_column(_TABLE, f"acabamento_{face}_unidade")
        op.drop_column(_TABLE, f"acabamento_{face}_descricao")
        op.drop_column(_TABLE, f"acabamento_{face}_ref_le")
    op.drop_column(_TABLE, "acabamento_editado_localmente")
