"""Add unified piece classification and configurable associations.

Revision ID: 20260712_51
Revises: 20260711_50
Create Date: 2026-07-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260712_51"
down_revision: str | Sequence[str] | None = "20260711_50"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Classify pieces and make existing component links generic/editable."""
    op.add_column(
        "def_pecas",
        sa.Column("natureza", sa.String(30), nullable=False, server_default="MATERIAL"),
    )
    op.add_column(
        "def_pecas",
        sa.Column("orientacao", sa.String(30), nullable=False, server_default="NEUTRA"),
    )
    op.add_column("def_pecas", sa.Column("funcao", sa.String(100), nullable=True))
    op.create_index("ix_def_pecas_natureza", "def_pecas", ["natureza"])
    op.create_index("ix_def_pecas_orientacao", "def_pecas", ["orientacao"])
    op.create_index("ix_def_pecas_funcao", "def_pecas", ["funcao"])

    op.execute(
        sa.text(
            "UPDATE def_pecas SET natureza = CASE "
            "WHEN sem_material = 1 THEN 'SERVICO' "
            "WHEN tipo_peca = 'COMPOSTA' THEN 'CONJUNTO' "
            "ELSE 'MATERIAL' END"
        )
    )

    op.add_column(
        "def_peca_componentes",
        sa.Column("zona_aplicacao", sa.String(30), nullable=False, server_default="GERAL"),
    )
    op.add_column(
        "def_peca_componentes",
        sa.Column("dimensao_referencia", sa.String(30), nullable=False, server_default="COMP"),
    )
    op.add_column(
        "def_peca_componentes",
        sa.Column("numero_topos", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_def_peca_componentes_zona_aplicacao",
        "def_peca_componentes",
        ["zona_aplicacao"],
    )
    op.create_check_constraint(
        "ck_def_peca_componentes_num_topos",
        "def_peca_componentes",
        "numero_topos IN (0, 1, 2)",
    )

    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT id FROM def_regras_quantidade WHERE codigo = :codigo"),
        {"codigo": "UNIAO_TOPOS_128"},
    ).first()
    if exists is None:
        bind.execute(
            sa.text(
                "INSERT INTO def_regras_quantidade "
                "(codigo, nome, expressao, descricao, ativo) "
                "VALUES (:codigo, :nome, :expressao, :descricao, :ativo)"
            ),
            {
                "codigo": "UNIAO_TOPOS_128",
                "nome": "Uniões por topo (intervalos de 128 mm)",
                "expressao": "MAX(2, CEIL(MEDIDA_TOPO / 128))",
                "descricao": (
                    "Quantidade por topo: mínimo 2; aumenta por intervalos de 128 mm. "
                    "O número de topos é aplicado separadamente pelo associado."
                ),
                "ativo": True,
            },
        )


def downgrade() -> None:
    """Remove the unified-piece foundation fields."""
    op.execute(
        sa.text(
            "DELETE FROM def_regras_quantidade WHERE codigo = 'UNIAO_TOPOS_128'"
        )
    )
    op.drop_constraint(
        "ck_def_peca_componentes_num_topos",
        "def_peca_componentes",
        type_="check",
    )
    op.drop_index(
        "ix_def_peca_componentes_zona_aplicacao",
        table_name="def_peca_componentes",
    )
    op.drop_column("def_peca_componentes", "numero_topos")
    op.drop_column("def_peca_componentes", "dimensao_referencia")
    op.drop_column("def_peca_componentes", "zona_aplicacao")

    op.drop_index("ix_def_pecas_funcao", table_name="def_pecas")
    op.drop_index("ix_def_pecas_orientacao", table_name="def_pecas")
    op.drop_index("ix_def_pecas_natureza", table_name="def_pecas")
    op.drop_column("def_pecas", "funcao")
    op.drop_column("def_pecas", "orientacao")
    op.drop_column("def_pecas", "natureza")
