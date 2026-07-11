"""Add exact ValueSet priority to piece associations and costing snapshots.

Revision ID: 20260715_54
Revises: 20260714_53
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260715_54"
down_revision: str | Sequence[str] | None = "20260714_53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "def_peca_componentes",
        sa.Column(
            "prioridade_valueset",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "orcamento_item_custeio_linhas",
        sa.Column("associado_valueset_prioridade", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column(
        "orcamento_item_custeio_linhas", "associado_valueset_prioridade"
    )
    op.drop_column("def_peca_componentes", "prioridade_valueset")
