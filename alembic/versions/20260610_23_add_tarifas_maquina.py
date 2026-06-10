"""Add machine tariffs (STD/SERIE) and CNC area price tiers (phase 8S.0).

Revision ID: 20260610_23
Revises: 20260609_22
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260610_23"
down_revision: str | Sequence[str] | None = "20260609_22"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MAQUINAS = "def_maquinas"
_NOVOS_CAMPOS = (
    "custo_hora_serie",
    "preco_ml_std",
    "preco_ml_serie",
    "custo_setup_peca_std",
    "custo_setup_peca_serie",
)
_ESCALOES = "def_maquina_escaloes_area"


def upgrade() -> None:
    """Add STD/SERIE tariffs to machines and create the CNC area-tier table."""
    for campo in _NOVOS_CAMPOS:
        op.add_column(_MAQUINAS, sa.Column(campo, sa.Numeric(14, 4), nullable=True))

    op.create_table(
        _ESCALOES,
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("def_maquina_id", sa.BigInteger(), nullable=False),
        sa.Column("nivel", sa.Integer(), server_default="1", nullable=False),
        sa.Column("area_max_m2", sa.Numeric(14, 4), nullable=True),
        sa.Column("preco_peca_std", sa.Numeric(14, 4), nullable=True),
        sa.Column("preco_peca_serie", sa.Numeric(14, 4), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["def_maquina_id"], ["def_maquinas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_def_maquina_escaloes_area_maquina", _ESCALOES, ["def_maquina_id"]
    )
    op.create_index("ix_def_maquina_escaloes_area_ativo", _ESCALOES, ["ativo"])


def downgrade() -> None:
    """Drop the CNC area-tier table and the machine tariffs."""
    op.drop_index("ix_def_maquina_escaloes_area_ativo", table_name=_ESCALOES)
    op.drop_index("ix_def_maquina_escaloes_area_maquina", table_name=_ESCALOES)
    op.drop_table(_ESCALOES)
    for campo in reversed(_NOVOS_CAMPOS):
        op.drop_column(_MAQUINAS, campo)
