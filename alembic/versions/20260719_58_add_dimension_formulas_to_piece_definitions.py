"""Add dimensional formulas to piece definitions and associations.

Revision ID: 20260719_58
Revises: 20260718_57
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_58"
down_revision: str | Sequence[str] | None = "20260718_57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in ("formula_comp", "formula_larg", "formula_esp"):
        op.add_column("def_pecas", sa.Column(column, sa.String(length=100), nullable=True))
        op.add_column(
            "def_peca_componentes",
            sa.Column(column, sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    for column in reversed(("formula_comp", "formula_larg", "formula_esp")):
        op.drop_column("def_peca_componentes", column)
        op.drop_column("def_pecas", column)
