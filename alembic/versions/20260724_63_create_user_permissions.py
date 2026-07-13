"""Create per-user application permissions.

Revision ID: 20260724_63
Revises: 20260723_62
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260724_63"
down_revision: str | Sequence[str] | None = "20260723_62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_key", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_permissions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_permissions"),
        sa.UniqueConstraint("user_id", "permission_key", name="uq_user_permissions_user_key"),
    )
    op.create_index("ix_user_permissions_user_id", "user_permissions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_permissions_user_id", table_name="user_permissions")
    op.drop_table("user_permissions")
