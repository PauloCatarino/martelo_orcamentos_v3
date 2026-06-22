"""Create orcamento_versao_eventos table (R2.6 audit log).

Revision ID: 20260622_45
Revises: 20260621_44
Create Date: 2026-06-22
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260622_45"
down_revision: str | Sequence[str] | None = "20260621_44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orcamento_versao_eventos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("orcamento_versao_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["orcamento_versao_id"], ["orcamento_versoes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_orcamento_versao_eventos_versao",
        "orcamento_versao_eventos",
        ["orcamento_versao_id"],
    )


def downgrade() -> None:
    op.drop_table("orcamento_versao_eventos")
