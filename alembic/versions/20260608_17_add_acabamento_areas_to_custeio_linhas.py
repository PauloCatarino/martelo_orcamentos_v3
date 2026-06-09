"""Add finishing (acabamento) faces and areas to item cost lines (phase 8M).

Revision ID: 20260608_17
Revises: 20260608_16
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_17"
down_revision: str | Sequence[str] | None = "20260608_16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add the finishing faces and computed areas (no cost yet)."""
    op.add_column(_TABLE, sa.Column("acabamento_face_sup", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("acabamento_face_inf", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("area_acabamento_sup", sa.Numeric(14, 4), nullable=True))
    op.add_column(_TABLE, sa.Column("area_acabamento_inf", sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    """Drop the finishing faces and areas."""
    op.drop_column(_TABLE, "area_acabamento_inf")
    op.drop_column(_TABLE, "area_acabamento_sup")
    op.drop_column(_TABLE, "acabamento_face_inf")
    op.drop_column(_TABLE, "acabamento_face_sup")
