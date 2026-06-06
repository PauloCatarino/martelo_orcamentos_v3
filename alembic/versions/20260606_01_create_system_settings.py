"""Create system settings table.

Revision ID: 20260606_01
Revises: 20260605_06
Create Date: 2026-06-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260606_01"
down_revision: str | Sequence[str] | None = "20260605_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create system_settings table."""
    op.create_table(
        "system_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("chave", sa.String(length=100), nullable=False),
        sa.Column("valor", sa.Text(), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(length=50), nullable=False, server_default="texto"),
        sa.Column("grupo", sa.String(length=100), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
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
        sa.PrimaryKeyConstraint("id", name="pk_system_settings"),
        sa.UniqueConstraint("chave", name="uq_system_settings_chave"),
    )
    op.create_index("ix_system_settings_grupo", "system_settings", ["grupo"], unique=False)
    op.create_index("ix_system_settings_tipo", "system_settings", ["tipo"], unique=False)
    op.create_index("ix_system_settings_ativo", "system_settings", ["ativo"], unique=False)


def downgrade() -> None:
    """Drop system_settings table."""
    op.drop_index("ix_system_settings_ativo", table_name="system_settings")
    op.drop_index("ix_system_settings_tipo", table_name="system_settings")
    op.drop_index("ix_system_settings_grupo", table_name="system_settings")
    op.drop_table("system_settings")
