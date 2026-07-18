"""Assign owner-less ValueSet models to the administrator.

Until now ``def_valueset_modelos.user_id`` was never filled, so every model
had no owner. With the per-user visibility (own + global) each model needs an
owner; legacy owner-less models are assigned to the administrator account so
they keep showing up (as the admin's own models) instead of silently
disappearing. Global models keep being shown to everyone regardless of owner.

Revision ID: 20260801_71
Revises: 20260731_70
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "20260801_71"
down_revision: str | Sequence[str] | None = "20260731_70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Give every owner-less model to the first administrator (if one exists)."""
    op.execute(
        "UPDATE def_valueset_modelos "
        "SET user_id = ("
        "  SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"
        ") "
        "WHERE user_id IS NULL "
        "  AND EXISTS (SELECT 1 FROM users WHERE role = 'admin')"
    )


def downgrade() -> None:
    """Irreversible: ownership set here may have since been edited by users."""
    # Data migration intentionally left irreversible to avoid clearing owners
    # that were changed after the upgrade.
    pass
