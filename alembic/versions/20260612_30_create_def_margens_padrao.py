"""Default margins per scope (phase 8T.1).

Creates ``def_margens_padrao``: the INITIAL margin values for new budgets,
with three scopes — one STANDARD record, one per customer and one per user
(unique on cliente_id/user_id; the single-STANDARD rule is enforced in the
service because MySQL has no partial unique indexes).

Also seeds the STANDARD record with the example values: lucro 10%, MP 15%,
mao de obra 5%, acabamentos 5%, administrativos 3%.

Revision ID: 20260612_30
Revises: 20260612_29
Create Date: 2026-06-12
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260612_30"
down_revision: str | Sequence[str] | None = "20260612_29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABELA = "def_margens_padrao"


def upgrade() -> None:
    """Create def_margens_padrao and seed the STANDARD record."""
    op.create_table(
        _TABELA,
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("ambito", sa.String(length=20), nullable=False),
        sa.Column(
            "cliente_id",
            sa.BigInteger(),
            sa.ForeignKey("clientes.id"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("margem_lucro_pct", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("margem_mp_pct", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("margem_mao_obra_pct", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("margem_acabamentos_pct", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column(
            "custos_administrativos_pct", sa.Numeric(8, 4), nullable=False, server_default="0"
        ),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("cliente_id", name="uq_def_margens_padrao_cliente"),
        sa.UniqueConstraint("user_id", name="uq_def_margens_padrao_user"),
    )
    op.create_index(
        "ix_def_margens_padrao_ambito", _TABELA, ["ambito"], unique=False
    )
    op.create_index(
        "ix_def_margens_padrao_cliente_id", _TABELA, ["cliente_id"], unique=False
    )
    op.create_index(
        "ix_def_margens_padrao_user_id", _TABELA, ["user_id"], unique=False
    )

    tabela = sa.table(
        _TABELA,
        sa.column("ambito", sa.String),
        sa.column("margem_lucro_pct", sa.Numeric),
        sa.column("margem_mp_pct", sa.Numeric),
        sa.column("margem_mao_obra_pct", sa.Numeric),
        sa.column("margem_acabamentos_pct", sa.Numeric),
        sa.column("custos_administrativos_pct", sa.Numeric),
        sa.column("ativo", sa.Boolean),
    )
    op.execute(
        tabela.insert().values(
            ambito="STANDARD",
            margem_lucro_pct=10,
            margem_mp_pct=15,
            margem_mao_obra_pct=5,
            margem_acabamentos_pct=5,
            custos_administrativos_pct=3,
            ativo=True,
        )
    )


def downgrade() -> None:
    """Drop def_margens_padrao."""
    op.drop_index("ix_def_margens_padrao_user_id", table_name=_TABELA)
    op.drop_index("ix_def_margens_padrao_cliente_id", table_name=_TABELA)
    op.drop_index("ix_def_margens_padrao_ambito", table_name=_TABELA)
    op.drop_table(_TABELA)
