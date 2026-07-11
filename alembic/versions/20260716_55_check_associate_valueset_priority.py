"""Protect associate ValueSet priority at database level.

Revision ID: 20260716_55
Revises: 20260715_54
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "20260716_55"
down_revision: str | Sequence[str] | None = "20260715_54"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOME = "ck_def_peca_componentes_prioridade_valueset_pos"
TABELA = "def_peca_componentes"


def upgrade() -> None:
    op.create_check_constraint(NOME, TABELA, "prioridade_valueset >= 1")


def downgrade() -> None:
    op.drop_constraint(NOME, TABELA, type_="check")
