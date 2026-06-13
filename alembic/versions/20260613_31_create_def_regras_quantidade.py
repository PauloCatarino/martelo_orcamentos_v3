"""Configurable quantity rules (phase 8T.5.0).

Creates ``def_regras_quantidade``: admin-defined expressions (over the main
piece's COMP/LARG/ESP/QT_PAI) that later compute hardware quantities. This phase
only stores the rules; the example rules are seeded by an idempotent script
(scripts/create_default_regras_quantidade.py), not here.

Revision ID: 20260613_31
Revises: 20260612_30
Create Date: 2026-06-13
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260613_31"
down_revision: str | Sequence[str] | None = "20260612_30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABELA = "def_regras_quantidade"


def upgrade() -> None:
    """Create def_regras_quantidade."""
    op.create_table(
        _TABELA,
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("expressao", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("codigo", name="uq_def_regras_quantidade_codigo"),
    )
    op.create_index(
        "ix_def_regras_quantidade_ativo", _TABELA, ["ativo"], unique=False
    )


def downgrade() -> None:
    """Drop def_regras_quantidade."""
    op.drop_index("ix_def_regras_quantidade_ativo", table_name=_TABELA)
    op.drop_table(_TABELA)
