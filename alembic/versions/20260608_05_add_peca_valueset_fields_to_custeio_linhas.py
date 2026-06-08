"""Add piece + ValueSet snapshot fields to item cost lines (phase 8E).

Revision ID: 20260608_05
Revises: 20260608_04
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260608_05"
down_revision: str | Sequence[str] | None = "20260608_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orcamento_item_custeio_linhas"


def upgrade() -> None:
    """Add piece identity and ValueSet snapshot columns to cost lines."""
    op.add_column(_TABLE, sa.Column("def_peca_id", sa.BigInteger(), nullable=True))
    op.add_column(_TABLE, sa.Column("def_peca_codigo", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("chave_valueset", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("codigo_orlas", sa.String(length=20), nullable=True))
    op.add_column(_TABLE, sa.Column("mat_default", sa.String(length=150), nullable=True))
    op.add_column(_TABLE, sa.Column("ref_le", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("descricao_no_orcamento", sa.Text(), nullable=True))
    op.add_column(_TABLE, sa.Column("preco_liquido", sa.Numeric(precision=14, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("desperdicio_percentagem", sa.Numeric(precision=8, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("tipo_materia_prima", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("familia_materia_prima", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("coresp_orla_0_4", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("coresp_orla_1_0", sa.String(length=100), nullable=True))
    op.add_column(_TABLE, sa.Column("comp_mp", sa.Numeric(precision=14, scale=3), nullable=True))
    op.add_column(_TABLE, sa.Column("larg_mp", sa.Numeric(precision=14, scale=3), nullable=True))
    op.add_column(_TABLE, sa.Column("esp_mp", sa.Numeric(precision=14, scale=3), nullable=True))
    op.add_column(_TABLE, sa.Column("qt_mod", sa.Numeric(precision=14, scale=4), nullable=True))
    op.add_column(_TABLE, sa.Column("qt_und", sa.Numeric(precision=14, scale=4), nullable=True))
    op.create_index("ix_oicl_def_peca_id", _TABLE, ["def_peca_id"], unique=False)
    op.create_index("ix_oicl_chave_valueset", _TABLE, ["chave_valueset"], unique=False)
    op.create_foreign_key(
        "fk_oicl_def_peca_id_def_pecas",
        _TABLE,
        "def_pecas",
        ["def_peca_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drop the piece identity and ValueSet snapshot columns."""
    op.drop_constraint("fk_oicl_def_peca_id_def_pecas", _TABLE, type_="foreignkey")
    op.drop_index("ix_oicl_chave_valueset", table_name=_TABLE)
    op.drop_index("ix_oicl_def_peca_id", table_name=_TABLE)
    op.drop_column(_TABLE, "qt_und")
    op.drop_column(_TABLE, "qt_mod")
    op.drop_column(_TABLE, "esp_mp")
    op.drop_column(_TABLE, "larg_mp")
    op.drop_column(_TABLE, "comp_mp")
    op.drop_column(_TABLE, "coresp_orla_1_0")
    op.drop_column(_TABLE, "coresp_orla_0_4")
    op.drop_column(_TABLE, "familia_materia_prima")
    op.drop_column(_TABLE, "tipo_materia_prima")
    op.drop_column(_TABLE, "desperdicio_percentagem")
    op.drop_column(_TABLE, "preco_liquido")
    op.drop_column(_TABLE, "descricao_no_orcamento")
    op.drop_column(_TABLE, "ref_le")
    op.drop_column(_TABLE, "mat_default")
    op.drop_column(_TABLE, "codigo_orlas")
    op.drop_column(_TABLE, "chave_valueset")
    op.drop_column(_TABLE, "def_peca_codigo")
    op.drop_column(_TABLE, "def_peca_id")
