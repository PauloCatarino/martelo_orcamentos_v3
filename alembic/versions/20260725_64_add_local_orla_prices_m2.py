"""Add local edge-band price snapshots in EUR/m2."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_64"
down_revision: str | Sequence[str] | None = "20260724_63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLES = (
    "def_valueset_modelo_linhas",
    "orcamento_valueset_linhas",
    "orcamento_item_valueset_linhas",
    "orcamento_item_custeio_linhas",
)


def upgrade() -> None:
    """Add nullable local snapshots; legacy rows keep compatibility fallback."""
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("preco_orla_0_4_m2", sa.Numeric(14, 4), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("preco_orla_1_0_m2", sa.Numeric(14, 4), nullable=True),
        )


def downgrade() -> None:
    """Remove local edge-band snapshots."""
    for table in reversed(_TABLES):
        op.drop_column(table, "preco_orla_1_0_m2")
        op.drop_column(table, "preco_orla_0_4_m2")
