"""Add enc_phc and free info fields (phase 9.1).

Revision ID: 20260618_39
Revises: 20260616_38
Create Date: 2026-06-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260618_39"
down_revision: str | Sequence[str] | None = "20260616_38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add general info fields to budgets and PHC order to versions."""
    op.add_column(
        "orcamento_versoes",
        sa.Column("enc_phc", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "orcamentos",
        sa.Column("info_1", sa.Text(), nullable=True),
    )
    op.add_column(
        "orcamentos",
        sa.Column("info_2", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop general info fields and PHC order."""
    op.drop_column("orcamentos", "info_2")
    op.drop_column("orcamentos", "info_1")
    op.drop_column("orcamento_versoes", "enc_phc")
