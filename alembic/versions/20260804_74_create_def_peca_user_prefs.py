"""Create the per-user piece library preferences table."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260804_74"
down_revision: str | Sequence[str] | None = "20260803_73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: def_peca_user_prefs (which pieces each user sees + favorites).

    A user without rows keeps the default behaviour (sees every active piece).
    Once rows exist, only the referenced pieces appear in that user's costing
    library; ``favorito`` marks the ones surfaced in the Favoritos group.
    """
    op.create_table(
        "def_peca_user_prefs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "def_peca_id",
            sa.BigInteger(),
            sa.ForeignKey("def_pecas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("favorito", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "def_peca_id", name="uq_def_peca_user_prefs_user_peca"
        ),
    )
    op.create_index(
        "ix_def_peca_user_prefs_user_id", "def_peca_user_prefs", ["user_id"]
    )
    op.create_index(
        "ix_def_peca_user_prefs_def_peca_id", "def_peca_user_prefs", ["def_peca_id"]
    )


def downgrade() -> None:
    """Remove the per-user piece library preferences table."""
    op.drop_index("ix_def_peca_user_prefs_def_peca_id", table_name="def_peca_user_prefs")
    op.drop_index("ix_def_peca_user_prefs_user_id", table_name="def_peca_user_prefs")
    op.drop_table("def_peca_user_prefs")
