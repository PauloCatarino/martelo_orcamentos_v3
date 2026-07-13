"""Create local effective operations for costing lines.

Revision ID: 20260723_62
Revises: 20260722_61
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_62"
down_revision: str | Sequence[str] | None = "20260722_61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orcamento_item_custeio_linha_operacoes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("linha_id", sa.BigInteger(), nullable=False),
        sa.Column("def_operacao_id", sa.BigInteger(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("tipo_operacao", sa.String(100), nullable=True),
        sa.Column("unidade_calculo", sa.String(50), nullable=True),
        sa.Column("maquina_id", sa.BigInteger(), nullable=True),
        sa.Column("origem", sa.String(40), nullable=False, server_default="LOCAL"),
        sa.Column("acao", sa.String(30), nullable=True),
        sa.Column("regra_calculo", sa.String(100), nullable=True),
        sa.Column("quantidade_base", sa.Numeric(14, 4), nullable=True),
        sa.Column("rasgo_qt_comp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rasgo_qt_larg", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tempo_setup_minutos", sa.Numeric(14, 4), nullable=True),
        sa.Column("tempo_por_unidade_minutos", sa.Numeric(14, 4), nullable=True),
        sa.Column("unidade_tempo", sa.String(50), nullable=True),
        sa.Column("obrigatorio", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["linha_id"], ["orcamento_item_custeio_linhas.id"],
            name="fk_oiclo_linha", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["def_operacao_id"], ["def_operacoes.id"], name="fk_oiclo_def_operacao"
        ),
        sa.ForeignKeyConstraint(
            ["maquina_id"], ["def_maquinas.id"], name="fk_oiclo_maquina"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_oiclo_linha_id", "orcamento_item_custeio_linha_operacoes", ["linha_id"])
    op.create_index("ix_oiclo_def_operacao_id", "orcamento_item_custeio_linha_operacoes", ["def_operacao_id"])
    op.create_index("ix_oiclo_maquina_id", "orcamento_item_custeio_linha_operacoes", ["maquina_id"])
    op.create_index("ix_oiclo_ativo", "orcamento_item_custeio_linha_operacoes", ["ativo"])


def downgrade() -> None:
    op.drop_table("orcamento_item_custeio_linha_operacoes")
