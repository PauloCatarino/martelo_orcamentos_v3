"""Persist the applied ValueSet priority on costing lines.

Revision ID: 20260718_57
Revises: 20260717_56
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260718_57"
down_revision: str | Sequence[str] | None = "20260717_56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orcamento_item_custeio_linhas",
        sa.Column("valueset_prioridade", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_oicl_valueset_prioridade_pos",
        "orcamento_item_custeio_linhas",
        "valueset_prioridade IS NULL OR valueset_prioridade >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_oicl_valueset_prioridade_pos",
        "orcamento_item_custeio_linhas",
        type_="check",
    )
    op.drop_column("orcamento_item_custeio_linhas", "valueset_prioridade")
