"""Link a quantity rule to a composite-piece component (phase 8T.5.1).

Adds ``def_regra_quantidade_id`` (nullable FK -> def_regras_quantidade.id) to
def_peca_componentes. When set, the component's quantity is computed by that
rule from the main piece's dimensions; when NULL the fixed quantidade /
regra_quantidade keeps being the fallback.

Revision ID: 20260613_32
Revises: 20260613_31
Create Date: 2026-06-13
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260613_32"
down_revision: str | Sequence[str] | None = "20260613_31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABELA = "def_peca_componentes"
_COLUNA = "def_regra_quantidade_id"
_FK = "fk_def_peca_componentes_regra_quantidade"
_IX = "ix_def_peca_componentes_regra_quantidade_id"


def upgrade() -> None:
    """Add the optional quantity-rule FK to the components table."""
    op.add_column(
        _TABELA,
        sa.Column(_COLUNA, sa.BigInteger(), nullable=True),
    )
    op.create_index(_IX, _TABELA, [_COLUNA], unique=False)
    op.create_foreign_key(
        _FK,
        _TABELA,
        "def_regras_quantidade",
        [_COLUNA],
        ["id"],
    )


def downgrade() -> None:
    """Drop the quantity-rule FK from the components table."""
    op.drop_constraint(_FK, _TABELA, type_="foreignkey")
    op.drop_index(_IX, table_name=_TABELA)
    op.drop_column(_TABELA, _COLUNA)
