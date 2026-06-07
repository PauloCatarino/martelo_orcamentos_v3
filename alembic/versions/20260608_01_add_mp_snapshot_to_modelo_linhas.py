"""Add materia-prima snapshot fields to def_valueset_modelo_linhas.

Revision ID: 20260608_01
Revises: 20260607_04
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_01"
down_revision: str | Sequence[str] | None = "20260607_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "def_valueset_modelo_linhas"


def upgrade() -> None:
    """Add the materia-prima snapshot columns."""
    op.add_column(_TABLE, sa.Column("ref_le", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("descricao_no_orcamento", sa.Text(), nullable=True))
    op.add_column(_TABLE, sa.Column("preco_tabela", sa.Numeric(precision=12, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("margem_percentagem", sa.Numeric(precision=8, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("desconto_percentagem", sa.Numeric(precision=8, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("preco_liquido", sa.Numeric(precision=12, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("unidade", sa.String(length=50), nullable=True))
    op.add_column(_TABLE, sa.Column("desperdicio_percentagem", sa.Numeric(precision=8, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("tipo_materia_prima", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("familia_materia_prima", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("coresp_orla_0_4", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("coresp_orla_1_0", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("comp_mp", sa.Numeric(precision=12, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("larg_mp", sa.Numeric(precision=12, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("esp_mp", sa.Numeric(precision=12, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("origem_dados", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Drop the materia-prima snapshot columns."""
    op.drop_column(_TABLE, "origem_dados")
    op.drop_column(_TABLE, "esp_mp")
    op.drop_column(_TABLE, "larg_mp")
    op.drop_column(_TABLE, "comp_mp")
    op.drop_column(_TABLE, "coresp_orla_1_0")
    op.drop_column(_TABLE, "coresp_orla_0_4")
    op.drop_column(_TABLE, "familia_materia_prima")
    op.drop_column(_TABLE, "tipo_materia_prima")
    op.drop_column(_TABLE, "desperdicio_percentagem")
    op.drop_column(_TABLE, "unidade")
    op.drop_column(_TABLE, "preco_liquido")
    op.drop_column(_TABLE, "desconto_percentagem")
    op.drop_column(_TABLE, "margem_percentagem")
    op.drop_column(_TABLE, "preco_tabela")
    op.drop_column(_TABLE, "descricao_no_orcamento")
    op.drop_column(_TABLE, "ref_le")
