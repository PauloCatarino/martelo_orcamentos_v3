"""Create descricoes_predefinidas table.

Revision ID: 20260621_43
Revises: 20260618_42
Create Date: 2026-06-21
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260621_43"
down_revision: str | Sequence[str] | None = "20260618_42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "descricoes_predefinidas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(length=1), nullable=False, server_default="-"),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_descricoes_predefinidas_user_id", "descricoes_predefinidas", ["user_id"]
    )


def downgrade() -> None:
    # On MySQL the user_id index backs the foreign key, so dropping it before
    # the table fails. Dropping the table removes the FK and its index together.
    op.drop_table("descricoes_predefinidas")
