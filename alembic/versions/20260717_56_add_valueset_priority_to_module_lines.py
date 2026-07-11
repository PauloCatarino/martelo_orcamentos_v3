"""Preserve exact ValueSet priority on reusable module lines.

Revision ID: 20260717_56
Revises: 20260716_55
Create Date: 2026-07-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260717_56"
down_revision: str | Sequence[str] | None = "20260716_55"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "def_modulo_linhas",
        sa.Column("prioridade_valueset", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_def_modulo_linhas_prioridade_valueset_pos",
        "def_modulo_linhas",
        "prioridade_valueset IS NULL OR prioridade_valueset >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_def_modulo_linhas_prioridade_valueset_pos",
        "def_modulo_linhas",
        type_="check",
    )
    op.drop_column("def_modulo_linhas", "prioridade_valueset")
