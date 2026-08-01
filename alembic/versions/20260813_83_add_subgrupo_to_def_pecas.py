"""Add def_pecas.subgrupo (sub-familias dentro de um grupo)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_83"
down_revision: str | Sequence[str] | None = "20260812_82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: uma sub-familia opcional dentro do grupo da peça.

    O grupo das ferragens vai crescer muito (dobradiças, corrediças, puxadores,
    roupeiros, iluminação...). A sub-familia e' so' arrumação: as arvores das
    Definições de Peças e da biblioteca do custeio passam a mostrar
    Grupo > Sub-familia > Peça. Fica a NULL em todas as peças existentes, que
    continuam a aparecer direto debaixo do grupo.
    """
    op.add_column(
        "def_pecas",
        sa.Column("subgrupo", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_def_pecas_subgrupo", "def_pecas", ["subgrupo"])


def downgrade() -> None:
    """Remove a sub-familia das peças."""
    op.drop_index("ix_def_pecas_subgrupo", table_name="def_pecas")
    op.drop_column("def_pecas", "subgrupo")
