"""Normalize budget status values.

Revision ID: 20260618_40
Revises: 20260618_39
Create Date: 2026-06-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "20260618_40"
down_revision: str | Sequence[str] | None = "20260618_39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Migrate old draft status values to the canonical initial status."""
    op.execute(
        "UPDATE orcamento_versoes "
        "SET estado = 'Falta Or\u00e7amentar' "
        "WHERE estado = 'rascunho'"
    )


def downgrade() -> None:
    """Do not revert data statuses that may have since been edited."""
    # Data migration intentionally left irreversible to avoid overwriting
    # statuses selected after the upgrade.
    pass
