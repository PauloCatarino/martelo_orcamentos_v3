"""Add explicit actions to ValueSet operations.

Revision ID: 20260714_53
Revises: 20260713_52
Create Date: 2026-07-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260714_53"
down_revision: str | Sequence[str] | None = "20260713_52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELAS = (
    "def_valueset_modelo_linha_operacoes",
    "orcamento_valueset_linha_operacoes",
    "orcamento_item_valueset_linha_operacoes",
)


def upgrade() -> None:
    """Make the old total override visible as an explicit replace action."""
    for tabela in TABELAS:
        op.add_column(
            tabela,
            sa.Column(
                "acao",
                sa.String(30),
                nullable=False,
                server_default="ADICIONAR",
            ),
        )
        op.execute(sa.text(f"UPDATE {tabela} SET acao = 'SUBSTITUIR'"))


def downgrade() -> None:
    for tabela in reversed(TABELAS):
        op.drop_column(tabela, "acao")
