"""Module/article library (phase 8U.0).

Creates ``def_modulos`` (reusable module templates: scope, category, image
path) and ``def_modulo_linhas`` (their parametric structure — pieces,
components, divisions, measure formulas, ValueSet key, orla code, quantity-rule
link; NO material/price snapshot). The lines cascade-delete with the module.

Revision ID: 20260614_33
Revises: 20260613_32
Create Date: 2026-06-14
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_33"
down_revision: str | Sequence[str] | None = "20260613_32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MODULOS = "def_modulos"
_LINHAS = "def_modulo_linhas"


def upgrade() -> None:
    """Create def_modulos and def_modulo_linhas."""
    op.create_table(
        _MODULOS,
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("codigo", sa.String(length=100), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ambito", sa.String(length=20), nullable=False, server_default="UTILIZADOR"),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("categoria", sa.String(length=30), nullable=False, server_default="OUTROS"),
        sa.Column("imagem_path", sa.String(length=500), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("codigo", name="uq_def_modulos_codigo"),
    )
    op.create_index("ix_def_modulos_ambito", _MODULOS, ["ambito"], unique=False)
    op.create_index("ix_def_modulos_categoria", _MODULOS, ["categoria"], unique=False)
    op.create_index("ix_def_modulos_user_id", _MODULOS, ["user_id"], unique=False)
    op.create_index("ix_def_modulos_ativo", _MODULOS, ["ativo"], unique=False)

    op.create_table(
        _LINHAS,
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "def_modulo_id",
            sa.BigInteger(),
            sa.ForeignKey("def_modulos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tipo_linha", sa.String(length=30), nullable=False, server_default="PECA"),
        sa.Column("def_peca_id", sa.BigInteger(), sa.ForeignKey("def_pecas.id"), nullable=True),
        sa.Column("def_peca_codigo", sa.String(length=50), nullable=True),
        sa.Column("codigo", sa.String(length=100), nullable=True),
        sa.Column("descricao", sa.String(length=255), nullable=True),
        sa.Column("descricao_livre", sa.String(length=255), nullable=True),
        sa.Column("qt_mod", sa.String(length=50), nullable=True),
        sa.Column("qt_und", sa.String(length=50), nullable=True),
        sa.Column("comp", sa.String(length=100), nullable=True),
        sa.Column("larg", sa.String(length=100), nullable=True),
        sa.Column("esp", sa.String(length=100), nullable=True),
        sa.Column("chave_valueset", sa.String(length=100), nullable=True),
        sa.Column("codigo_orlas", sa.String(length=10), nullable=True),
        sa.Column(
            "def_regra_quantidade_id",
            sa.BigInteger(),
            sa.ForeignKey("def_regras_quantidade.id"),
            nullable=True,
        ),
        sa.Column("linha_pai_ordem", sa.Integer(), nullable=True),
        sa.Column("nivel", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_def_modulo_linhas_def_modulo_id", _LINHAS, ["def_modulo_id"], unique=False
    )
    op.create_index("ix_def_modulo_linhas_ativo", _LINHAS, ["ativo"], unique=False)


def downgrade() -> None:
    """Drop def_modulo_linhas and def_modulos."""
    op.drop_index("ix_def_modulo_linhas_ativo", table_name=_LINHAS)
    op.drop_index("ix_def_modulo_linhas_def_modulo_id", table_name=_LINHAS)
    op.drop_table(_LINHAS)

    op.drop_index("ix_def_modulos_ativo", table_name=_MODULOS)
    op.drop_index("ix_def_modulos_user_id", table_name=_MODULOS)
    op.drop_index("ix_def_modulos_categoria", table_name=_MODULOS)
    op.drop_index("ix_def_modulos_ambito", table_name=_MODULOS)
    op.drop_table(_MODULOS)
