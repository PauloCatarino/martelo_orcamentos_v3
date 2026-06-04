"""Create base budget models.

Revision ID: 20260604_01
Revises:
Create Date: 2026-06-04
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260604_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial budget model tables."""
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    op.create_table(
        "clientes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("nome_simplex", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("telefone", sa.String(length=50), nullable=True),
        sa.Column("telemovel", sa.String(length=50), nullable=True),
        sa.Column("morada", sa.Text(), nullable=True),
        sa.Column("num_cliente_phc", sa.String(length=50), nullable=True),
        sa.Column("source_system", sa.String(length=50), nullable=True),
        sa.Column("is_temporary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_clientes"),
    )
    op.create_index("ix_clientes_nome", "clientes", ["nome"], unique=False)
    op.create_index("ix_clientes_nome_simplex", "clientes", ["nome_simplex"], unique=False)
    op.create_index("ix_clientes_num_cliente_phc", "clientes", ["num_cliente_phc"], unique=False)

    op.create_table(
        "orcamentos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("num_orcamento", sa.String(length=32), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("obra", sa.String(length=255), nullable=True),
        sa.Column("localizacao", sa.String(length=255), nullable=True),
        sa.Column("ref_cliente", sa.String(length=255), nullable=True),
        sa.Column("created_by_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_by_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], name="fk_orcamentos_cliente_id_clientes"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name="fk_orcamentos_created_by_id_users"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], name="fk_orcamentos_updated_by_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_orcamentos"),
        sa.UniqueConstraint("ano", "num_orcamento", name="uq_orcamentos_ano_num_orcamento"),
    )
    op.create_index("ix_orcamentos_ano", "orcamentos", ["ano"], unique=False)
    op.create_index("ix_orcamentos_cliente_id", "orcamentos", ["cliente_id"], unique=False)
    op.create_index("ix_orcamentos_created_by_id", "orcamentos", ["created_by_id"], unique=False)
    op.create_index("ix_orcamentos_num_orcamento", "orcamentos", ["num_orcamento"], unique=False)
    op.create_index("ix_orcamentos_updated_by_id", "orcamentos", ["updated_by_id"], unique=False)

    op.create_table(
        "orcamento_versoes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("orcamento_id", sa.BigInteger(), nullable=False),
        sa.Column("numero_versao", sa.Integer(), nullable=False),
        sa.Column("codigo_versao", sa.String(length=50), nullable=False),
        sa.Column("estado", sa.String(length=50), nullable=False),
        sa.Column("preco_total", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("preco_origem", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_by_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name="fk_orcamento_versoes_created_by_id_users"),
        sa.ForeignKeyConstraint(["orcamento_id"], ["orcamentos.id"], name="fk_orcamento_versoes_orcamento_id_orcamentos"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], name="fk_orcamento_versoes_updated_by_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_orcamento_versoes"),
        sa.UniqueConstraint("codigo_versao", name="uq_orcamento_versoes_codigo"),
        sa.UniqueConstraint("orcamento_id", "numero_versao", name="uq_orcamento_versoes_orcamento_numero"),
    )
    op.create_index("ix_orcamento_versoes_codigo_versao", "orcamento_versoes", ["codigo_versao"], unique=False)
    op.create_index("ix_orcamento_versoes_created_by_id", "orcamento_versoes", ["created_by_id"], unique=False)
    op.create_index("ix_orcamento_versoes_orcamento_id", "orcamento_versoes", ["orcamento_id"], unique=False)
    op.create_index("ix_orcamento_versoes_updated_by_id", "orcamento_versoes", ["updated_by_id"], unique=False)

    op.create_table(
        "orcamento_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("orcamento_versao_id", sa.BigInteger(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=100), nullable=True),
        sa.Column("item", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("altura", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("largura", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("profundidade", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("quantidade", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unidade", sa.String(length=50), nullable=True),
        sa.Column("preco_unitario", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("preco_total", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("ajuste", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["orcamento_versao_id"],
            ["orcamento_versoes.id"],
            name="fk_orcamento_items_orcamento_versao_id_versoes",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_orcamento_items"),
        sa.UniqueConstraint("orcamento_versao_id", "ordem", name="uq_orcamento_items_versao_ordem"),
    )
    op.create_index("ix_orcamento_items_codigo", "orcamento_items", ["codigo"], unique=False)
    op.create_index("ix_orcamento_items_orcamento_versao_id", "orcamento_items", ["orcamento_versao_id"], unique=False)

    op.create_table(
        "orcamento_item_variaveis",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("valor", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("unidade", sa.String(length=50), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["item_id"], ["orcamento_items.id"], name="fk_orcamento_item_variaveis_item_id_items"),
        sa.PrimaryKeyConstraint("id", name="pk_orcamento_item_variaveis"),
        sa.UniqueConstraint("item_id", "nome", name="uq_orcamento_item_variaveis_item_nome"),
        sa.UniqueConstraint("item_id", "ordem", name="uq_orcamento_item_variaveis_item_ordem"),
    )
    op.create_index("ix_orcamento_item_variaveis_item_id", "orcamento_item_variaveis", ["item_id"], unique=False)


def downgrade() -> None:
    """Drop initial budget model tables."""
    op.drop_index("ix_orcamento_item_variaveis_item_id", table_name="orcamento_item_variaveis")
    op.drop_table("orcamento_item_variaveis")

    op.drop_index("ix_orcamento_items_orcamento_versao_id", table_name="orcamento_items")
    op.drop_index("ix_orcamento_items_codigo", table_name="orcamento_items")
    op.drop_table("orcamento_items")

    op.drop_index("ix_orcamento_versoes_updated_by_id", table_name="orcamento_versoes")
    op.drop_index("ix_orcamento_versoes_orcamento_id", table_name="orcamento_versoes")
    op.drop_index("ix_orcamento_versoes_created_by_id", table_name="orcamento_versoes")
    op.drop_index("ix_orcamento_versoes_codigo_versao", table_name="orcamento_versoes")
    op.drop_table("orcamento_versoes")

    op.drop_index("ix_orcamentos_updated_by_id", table_name="orcamentos")
    op.drop_index("ix_orcamentos_num_orcamento", table_name="orcamentos")
    op.drop_index("ix_orcamentos_created_by_id", table_name="orcamentos")
    op.drop_index("ix_orcamentos_cliente_id", table_name="orcamentos")
    op.drop_index("ix_orcamentos_ano", table_name="orcamentos")
    op.drop_table("orcamentos")

    op.drop_index("ix_clientes_num_cliente_phc", table_name="clientes")
    op.drop_index("ix_clientes_nome_simplex", table_name="clientes")
    op.drop_index("ix_clientes_nome", table_name="clientes")
    op.drop_table("clientes")

    op.drop_table("users")
