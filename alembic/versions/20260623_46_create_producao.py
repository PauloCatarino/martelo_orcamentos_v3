"""Create production process table.

Revision ID: 20260623_46
Revises: 20260622_45
Create Date: 2026-06-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260623_46"
down_revision: str | Sequence[str] | None = "20260622_45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "producao"


def upgrade() -> None:
    """Create producao."""
    op.create_table(
        _TABLE,
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("codigo_processo", sa.String(length=32), nullable=False),
        sa.Column("ano", sa.String(length=4), nullable=False),
        sa.Column("num_enc_phc", sa.String(length=16), nullable=False),
        sa.Column("versao_obra", sa.String(length=2), nullable=False, server_default="01"),
        sa.Column("versao_plano", sa.String(length=2), nullable=False, server_default="01"),
        sa.Column(
            "orcamento_id",
            sa.BigInteger(),
            sa.ForeignKey("orcamentos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cliente_id",
            sa.BigInteger(),
            sa.ForeignKey("clientes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("responsavel", sa.String(length=100), nullable=True),
        sa.Column("estado", sa.String(length=50), nullable=True),
        sa.Column("nome_cliente", sa.String(length=255), nullable=True),
        sa.Column("nome_cliente_simplex", sa.String(length=255), nullable=True),
        sa.Column("num_cliente_phc", sa.String(length=64), nullable=True),
        sa.Column("ref_cliente", sa.String(length=64), nullable=True),
        sa.Column("num_orcamento", sa.String(length=16), nullable=True),
        sa.Column("versao_orc", sa.String(length=2), nullable=True),
        sa.Column("obra", sa.String(length=255), nullable=True),
        sa.Column("localizacao", sa.String(length=255), nullable=True),
        sa.Column("descricao_orcamento", sa.Text(), nullable=True),
        sa.Column("data_inicio", sa.String(length=10), nullable=True),
        sa.Column("data_entrega", sa.String(length=10), nullable=True),
        sa.Column("preco_total", sa.Numeric(14, 2), nullable=True),
        sa.Column("qt_artigos", sa.Integer(), nullable=True),
        sa.Column("descricao_artigos", sa.Text(), nullable=True),
        sa.Column("materias_usados", sa.Text(), nullable=True),
        sa.Column("descricao_producao", sa.Text(), nullable=True),
        sa.Column("notas1", sa.Text(), nullable=True),
        sa.Column("notas2", sa.Text(), nullable=True),
        sa.Column("notas3", sa.Text(), nullable=True),
        sa.Column("imagem_path", sa.String(length=1024), nullable=True),
        sa.Column("pasta_servidor", sa.String(length=1024), nullable=True),
        sa.Column("tipo_pasta", sa.String(length=64), nullable=True),
        sa.Column("created_by_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("codigo_processo", name="uq_producao_codigo"),
        sa.UniqueConstraint(
            "ano",
            "num_enc_phc",
            "versao_obra",
            "versao_plano",
            name="uq_producao_chave",
        ),
    )
    op.create_index("ix_producao_codigo_processo", _TABLE, ["codigo_processo"], unique=False)
    op.create_index("ix_producao_ano", _TABLE, ["ano"], unique=False)
    op.create_index("ix_producao_num_enc_phc", _TABLE, ["num_enc_phc"], unique=False)
    op.create_index("ix_producao_orcamento_id", _TABLE, ["orcamento_id"], unique=False)
    op.create_index("ix_producao_cliente_id", _TABLE, ["cliente_id"], unique=False)
    op.create_index("ix_producao_estado", _TABLE, ["estado"], unique=False)
    op.create_index("ix_producao_nome_cliente", _TABLE, ["nome_cliente"], unique=False)
    op.create_index("ix_producao_created_by_id", _TABLE, ["created_by_id"], unique=False)
    op.create_index("ix_producao_updated_by_id", _TABLE, ["updated_by_id"], unique=False)


def downgrade() -> None:
    """Drop producao."""
    op.drop_index("ix_producao_updated_by_id", table_name=_TABLE)
    op.drop_index("ix_producao_created_by_id", table_name=_TABLE)
    op.drop_index("ix_producao_nome_cliente", table_name=_TABLE)
    op.drop_index("ix_producao_estado", table_name=_TABLE)
    op.drop_index("ix_producao_cliente_id", table_name=_TABLE)
    op.drop_index("ix_producao_orcamento_id", table_name=_TABLE)
    op.drop_index("ix_producao_num_enc_phc", table_name=_TABLE)
    op.drop_index("ix_producao_ano", table_name=_TABLE)
    op.drop_index("ix_producao_codigo_processo", table_name=_TABLE)
    op.drop_table(_TABLE)
