"""Create budget item cost lines.

Revision ID: 20260606_04
Revises: 20260606_03
Create Date: 2026-06-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260606_04"
down_revision: str | Sequence[str] | None = "20260606_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create orcamento_item_custeio_linhas table."""
    op.create_table(
        "orcamento_item_custeio_linhas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("orcamento_item_id", sa.BigInteger(), nullable=False),
        sa.Column("orcamento_item_modulo_id", sa.BigInteger(), nullable=True),
        sa.Column("origem_tipo", sa.String(length=100), nullable=True),
        sa.Column("origem_id", sa.Integer(), nullable=True),
        sa.Column("tipo_linha", sa.String(length=100), nullable=False),
        sa.Column("codigo", sa.String(length=100), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("materia_prima_id", sa.BigInteger(), nullable=True),
        sa.Column("ref_materia_prima", sa.String(length=100), nullable=True),
        sa.Column("descricao_materia_prima", sa.Text(), nullable=True),
        sa.Column("unidade", sa.String(length=30), nullable=True),
        sa.Column("quantidade", sa.Numeric(precision=14, scale=4), nullable=False, server_default="1"),
        sa.Column("comp", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("larg", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("esp", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("area_m2", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("perimetro_ml", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("ml_orla_fina", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("ml_orla_grossa", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("custo_unitario", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("custo_total", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("margem_percentagem", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("preco_unitario", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("preco_total", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("def_operacao_id", sa.BigInteger(), nullable=True),
        sa.Column("def_maquina_id", sa.BigInteger(), nullable=True),
        sa.Column("tempo_calculado", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("tempo_manual", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("override_manual", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("editado_localmente", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["orcamento_item_id"],
            ["orcamento_items.id"],
            name="fk_oicl_orcamento_item_id_orcamento_items",
        ),
        sa.ForeignKeyConstraint(
            ["orcamento_item_modulo_id"],
            ["orcamento_item_modulos.id"],
            name="fk_oicl_orcamento_item_modulo_id_orcamento_item_modulos",
        ),
        sa.ForeignKeyConstraint(
            ["materia_prima_id"],
            ["def_materias_primas.id"],
            name="fk_oicl_materia_prima_id_def_materias_primas",
        ),
        sa.ForeignKeyConstraint(
            ["def_operacao_id"],
            ["def_operacoes.id"],
            name="fk_oicl_def_operacao_id_def_operacoes",
        ),
        sa.ForeignKeyConstraint(
            ["def_maquina_id"],
            ["def_maquinas.id"],
            name="fk_oicl_def_maquina_id_def_maquinas",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_orcamento_item_custeio_linhas"),
    )
    op.create_index(
        "ix_oicl_orcamento_item_id",
        "orcamento_item_custeio_linhas",
        ["orcamento_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_oicl_orcamento_item_modulo_id",
        "orcamento_item_custeio_linhas",
        ["orcamento_item_modulo_id"],
        unique=False,
    )
    op.create_index(
        "ix_oicl_tipo_linha",
        "orcamento_item_custeio_linhas",
        ["tipo_linha"],
        unique=False,
    )
    op.create_index(
        "ix_oicl_origem_tipo",
        "orcamento_item_custeio_linhas",
        ["origem_tipo"],
        unique=False,
    )
    op.create_index(
        "ix_oicl_materia_prima_id",
        "orcamento_item_custeio_linhas",
        ["materia_prima_id"],
        unique=False,
    )
    op.create_index(
        "ix_oicl_def_operacao_id",
        "orcamento_item_custeio_linhas",
        ["def_operacao_id"],
        unique=False,
    )
    op.create_index(
        "ix_oicl_def_maquina_id",
        "orcamento_item_custeio_linhas",
        ["def_maquina_id"],
        unique=False,
    )
    op.create_index(
        "ix_oicl_ativo",
        "orcamento_item_custeio_linhas",
        ["ativo"],
        unique=False,
    )


def downgrade() -> None:
    """Drop orcamento_item_custeio_linhas table."""
    op.drop_index("ix_oicl_ativo", table_name="orcamento_item_custeio_linhas")
    op.drop_index("ix_oicl_def_maquina_id", table_name="orcamento_item_custeio_linhas")
    op.drop_index("ix_oicl_def_operacao_id", table_name="orcamento_item_custeio_linhas")
    op.drop_index("ix_oicl_materia_prima_id", table_name="orcamento_item_custeio_linhas")
    op.drop_index("ix_oicl_origem_tipo", table_name="orcamento_item_custeio_linhas")
    op.drop_index("ix_oicl_tipo_linha", table_name="orcamento_item_custeio_linhas")
    op.drop_index("ix_oicl_orcamento_item_modulo_id", table_name="orcamento_item_custeio_linhas")
    op.drop_index("ix_oicl_orcamento_item_id", table_name="orcamento_item_custeio_linhas")
    op.drop_table("orcamento_item_custeio_linhas")
