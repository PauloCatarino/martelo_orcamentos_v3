"""Store cost line comp/larg/esp as text expressions (phase 8G.1).

Revision ID: 20260608_08
Revises: 20260608_07
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_08"
down_revision: str | Sequence[str] | None = "20260608_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Change comp/larg/esp from numeric to text so they hold expressions."""
    for column in ("comp", "larg", "esp"):
        op.alter_column(
            _TABLE,
            column,
            existing_type=sa.Numeric(precision=14, scale=3),
            type_=sa.String(length=100),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Revert comp/larg/esp back to numeric."""
    for column in ("comp", "larg", "esp"):
        op.alter_column(
            _TABLE,
            column,
            existing_type=sa.String(length=100),
            type_=sa.Numeric(precision=14, scale=3),
            existing_nullable=True,
            postgresql_using=f"{column}::numeric",
        )
