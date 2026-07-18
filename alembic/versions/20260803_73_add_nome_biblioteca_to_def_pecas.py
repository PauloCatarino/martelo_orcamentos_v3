"""Add the library display name to piece definitions."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260803_73"
down_revision: str | Sequence[str] | None = "20260802_72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: def_pecas.nome_biblioteca (text shown in the costing library).

    When filled, the costing library tree shows this text instead of the
    piece name; empty keeps the current behaviour (name + orla code).
    """
    op.add_column(
        "def_pecas",
        sa.Column("nome_biblioteca", sa.String(150), nullable=True),
    )


def downgrade() -> None:
    """Remove the library display name column."""
    op.drop_column("def_pecas", "nome_biblioteca")
