"""Snapshot associate quantity rules on costing lines.

Revision ID: 20260713_52
Revises: 20260712_51
Create Date: 2026-07-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260713_52"
down_revision: str | Sequence[str] | None = "20260712_51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "def_peca_componentes",
        sa.Column("modo_quantidade", sa.String(30), nullable=False, server_default="TOTAL"),
    )

    tabela = "orcamento_item_custeio_linhas"
    op.add_column(tabela, sa.Column("associado_regra_codigo", sa.String(100), nullable=True))
    op.add_column(tabela, sa.Column("associado_regra_expressao", sa.Text(), nullable=True))
    op.add_column(tabela, sa.Column("associado_modo_quantidade", sa.String(30), nullable=True))
    op.add_column(tabela, sa.Column("associado_zona_aplicacao", sa.String(30), nullable=True))
    op.add_column(tabela, sa.Column("associado_dimensao_referencia", sa.String(30), nullable=True))
    op.add_column(tabela, sa.Column("associado_numero_topos", sa.Integer(), nullable=True))
    op.add_column(tabela, sa.Column("operacoes_snapshot_json", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_oicl_assoc_num_topos",
        tabela,
        "associado_numero_topos IS NULL OR associado_numero_topos IN (0, 1, 2)",
    )


def downgrade() -> None:
    tabela = "orcamento_item_custeio_linhas"
    op.drop_constraint("ck_oicl_assoc_num_topos", tabela, type_="check")
    op.drop_column(tabela, "operacoes_snapshot_json")
    op.drop_column(tabela, "associado_numero_topos")
    op.drop_column(tabela, "associado_dimensao_referencia")
    op.drop_column(tabela, "associado_zona_aplicacao")
    op.drop_column(tabela, "associado_modo_quantidade")
    op.drop_column(tabela, "associado_regra_expressao")
    op.drop_column(tabela, "associado_regra_codigo")
    op.drop_column("def_peca_componentes", "modo_quantidade")
