"""Create composite piece components.

Revision ID: 20260605_04
Revises: 20260605_03
Create Date: 2026-06-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_04"
down_revision: str | Sequence[str] | None = "20260605_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create def_peca_componentes table."""
    op.create_table(
        "def_peca_componentes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("def_peca_pai_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_componente", sa.String(length=50), nullable=False, server_default="PECA"),
        sa.Column("def_peca_componente_id", sa.BigInteger(), nullable=True),
        sa.Column("referencia_componente", sa.String(length=150), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("quantidade", sa.Numeric(precision=12, scale=3), nullable=False, server_default="1"),
        sa.Column("regra_quantidade", sa.String(length=100), nullable=True, server_default="FIXA"),
        sa.Column("obrigatorio", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["def_peca_pai_id"],
            ["def_pecas.id"],
            name="fk_def_peca_componentes_pai_id_def_pecas",
        ),
        sa.ForeignKeyConstraint(
            ["def_peca_componente_id"],
            ["def_pecas.id"],
            name="fk_def_peca_componentes_componente_id_def_pecas",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_def_peca_componentes"),
        sa.UniqueConstraint("def_peca_pai_id", "ordem", name="uq_def_peca_componentes_pai_ordem"),
    )
    op.create_index("ix_def_peca_componentes_def_peca_pai_id", "def_peca_componentes", ["def_peca_pai_id"])
    op.create_index(
        "ix_def_peca_componentes_def_peca_componente_id",
        "def_peca_componentes",
        ["def_peca_componente_id"],
    )
    op.create_index("ix_def_peca_componentes_tipo_componente", "def_peca_componentes", ["tipo_componente"])
    op.create_index("ix_def_peca_componentes_ativo", "def_peca_componentes", ["ativo"])


def downgrade() -> None:
    """Drop def_peca_componentes table."""
    op.drop_index("ix_def_peca_componentes_ativo", table_name="def_peca_componentes")
    op.drop_index("ix_def_peca_componentes_tipo_componente", table_name="def_peca_componentes")
    op.drop_index("ix_def_peca_componentes_def_peca_componente_id", table_name="def_peca_componentes")
    op.drop_index("ix_def_peca_componentes_def_peca_pai_id", table_name="def_peca_componentes")
    op.drop_table("def_peca_componentes")
