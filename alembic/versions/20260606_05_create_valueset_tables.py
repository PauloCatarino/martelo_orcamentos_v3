"""Create ValueSet base tables.

Revision ID: 20260606_05
Revises: 20260606_04
Create Date: 2026-06-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260606_05"
down_revision: str | Sequence[str] | None = "20260606_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create ValueSet model, budget-level, and item-level tables."""
    op.create_table(
        "def_valueset_modelos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=100), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(length=100), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_def_valueset_modelos"),
        sa.UniqueConstraint("codigo", name="uq_def_valueset_modelos_codigo"),
    )
    op.create_index("ix_dvm_codigo", "def_valueset_modelos", ["codigo"], unique=False)
    op.create_index("ix_dvm_ativo", "def_valueset_modelos", ["ativo"], unique=False)

    op.create_table(
        "def_valueset_modelo_linhas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("def_valueset_modelo_id", sa.BigInteger(), nullable=False),
        sa.Column("chave", sa.String(length=100), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=True),
        sa.Column("materia_prima_id", sa.BigInteger(), nullable=True),
        sa.Column("ref_materia_prima", sa.String(length=100), nullable=True),
        sa.Column("descricao_materia_prima", sa.Text(), nullable=True),
        sa.Column("valor_texto", sa.Text(), nullable=True),
        sa.Column("origem", sa.String(length=100), nullable=True),
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
            ["def_valueset_modelo_id"],
            ["def_valueset_modelos.id"],
            name="fk_dvml_modelo",
        ),
        sa.ForeignKeyConstraint(
            ["materia_prima_id"],
            ["def_materias_primas.id"],
            name="fk_dvml_materia_prima",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_def_valueset_modelo_linhas"),
        sa.UniqueConstraint(
            "def_valueset_modelo_id",
            "chave",
            name="uq_def_valueset_modelo_linhas_modelo_chave",
        ),
    )
    op.create_index(
        "ix_dvml_modelo_id",
        "def_valueset_modelo_linhas",
        ["def_valueset_modelo_id"],
        unique=False,
    )
    op.create_index("ix_dvml_chave", "def_valueset_modelo_linhas", ["chave"], unique=False)
    op.create_index(
        "ix_dvml_materia_prima_id",
        "def_valueset_modelo_linhas",
        ["materia_prima_id"],
        unique=False,
    )
    op.create_index("ix_dvml_ativo", "def_valueset_modelo_linhas", ["ativo"], unique=False)

    op.create_table(
        "orcamento_valueset_linhas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("orcamento_versao_id", sa.BigInteger(), nullable=False),
        sa.Column("chave", sa.String(length=100), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=True),
        sa.Column("materia_prima_id", sa.BigInteger(), nullable=True),
        sa.Column("ref_materia_prima", sa.String(length=100), nullable=True),
        sa.Column("descricao_materia_prima", sa.Text(), nullable=True),
        sa.Column("valor_texto", sa.Text(), nullable=True),
        sa.Column("origem", sa.String(length=100), nullable=True),
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
            ["orcamento_versao_id"],
            ["orcamento_versoes.id"],
            name="fk_ovl_orcamento_versao",
        ),
        sa.ForeignKeyConstraint(
            ["materia_prima_id"],
            ["def_materias_primas.id"],
            name="fk_ovl_materia_prima",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_orcamento_valueset_linhas"),
        sa.UniqueConstraint(
            "orcamento_versao_id",
            "chave",
            name="uq_orcamento_valueset_linhas_versao_chave",
        ),
    )
    op.create_index(
        "ix_ovl_orcamento_versao_id",
        "orcamento_valueset_linhas",
        ["orcamento_versao_id"],
        unique=False,
    )
    op.create_index("ix_ovl_chave", "orcamento_valueset_linhas", ["chave"], unique=False)
    op.create_index(
        "ix_ovl_materia_prima_id",
        "orcamento_valueset_linhas",
        ["materia_prima_id"],
        unique=False,
    )
    op.create_index("ix_ovl_ativo", "orcamento_valueset_linhas", ["ativo"], unique=False)

    op.create_table(
        "orcamento_item_valueset_linhas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("orcamento_item_id", sa.BigInteger(), nullable=False),
        sa.Column("chave", sa.String(length=100), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=True),
        sa.Column("materia_prima_id", sa.BigInteger(), nullable=True),
        sa.Column("ref_materia_prima", sa.String(length=100), nullable=True),
        sa.Column("descricao_materia_prima", sa.Text(), nullable=True),
        sa.Column("valor_texto", sa.Text(), nullable=True),
        sa.Column("origem", sa.String(length=100), nullable=True),
        sa.Column("herdado_do_orcamento", sa.Boolean(), nullable=False, server_default=sa.text("1")),
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
            name="fk_oivl_orcamento_item",
        ),
        sa.ForeignKeyConstraint(
            ["materia_prima_id"],
            ["def_materias_primas.id"],
            name="fk_oivl_materia_prima",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_orcamento_item_valueset_linhas"),
        sa.UniqueConstraint(
            "orcamento_item_id",
            "chave",
            name="uq_orcamento_item_valueset_linhas_item_chave",
        ),
    )
    op.create_index(
        "ix_oivl_orcamento_item_id",
        "orcamento_item_valueset_linhas",
        ["orcamento_item_id"],
        unique=False,
    )
    op.create_index("ix_oivl_chave", "orcamento_item_valueset_linhas", ["chave"], unique=False)
    op.create_index(
        "ix_oivl_materia_prima_id",
        "orcamento_item_valueset_linhas",
        ["materia_prima_id"],
        unique=False,
    )
    op.create_index("ix_oivl_ativo", "orcamento_item_valueset_linhas", ["ativo"], unique=False)


def downgrade() -> None:
    """Drop ValueSet base tables."""
    op.drop_index("ix_oivl_ativo", table_name="orcamento_item_valueset_linhas")
    op.drop_index("ix_oivl_materia_prima_id", table_name="orcamento_item_valueset_linhas")
    op.drop_index("ix_oivl_chave", table_name="orcamento_item_valueset_linhas")
    op.drop_index("ix_oivl_orcamento_item_id", table_name="orcamento_item_valueset_linhas")
    op.drop_table("orcamento_item_valueset_linhas")

    op.drop_index("ix_ovl_ativo", table_name="orcamento_valueset_linhas")
    op.drop_index("ix_ovl_materia_prima_id", table_name="orcamento_valueset_linhas")
    op.drop_index("ix_ovl_chave", table_name="orcamento_valueset_linhas")
    op.drop_index("ix_ovl_orcamento_versao_id", table_name="orcamento_valueset_linhas")
    op.drop_table("orcamento_valueset_linhas")

    op.drop_index("ix_dvml_ativo", table_name="def_valueset_modelo_linhas")
    op.drop_index("ix_dvml_materia_prima_id", table_name="def_valueset_modelo_linhas")
    op.drop_index("ix_dvml_chave", table_name="def_valueset_modelo_linhas")
    op.drop_index("ix_dvml_modelo_id", table_name="def_valueset_modelo_linhas")
    op.drop_table("def_valueset_modelo_linhas")

    op.drop_index("ix_dvm_ativo", table_name="def_valueset_modelos")
    op.drop_index("ix_dvm_codigo", table_name="def_valueset_modelos")
    op.drop_table("def_valueset_modelos")
