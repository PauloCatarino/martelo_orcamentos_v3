"""Add cost-exclusion flags to item cost lines (phase 8L).

Revision ID: 20260608_16
Revises: 20260608_15
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_16"
down_revision: str | Sequence[str] | None = "20260608_15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"
_FLAGS = (
    "excluir_mp",
    "excluir_orla",
    "excluir_ferragem",
    "excluir_producao",
    "excluir_acabamento",
    "excluir_mo",
)


def upgrade() -> None:
    """Add the excluir_* boolean flags (default 0 -> cost included)."""
    for flag in _FLAGS:
        op.add_column(
            _TABLE,
            sa.Column(flag, sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    """Drop the excluir_* flags."""
    for flag in reversed(_FLAGS):
        op.drop_column(_TABLE, flag)
