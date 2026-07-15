"""Add explicit budget margin profile and Cliente Final scope."""

from __future__ import annotations
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260727_66"
down_revision: str | Sequence[str] | None = "20260726_65"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing versions retain their actual copied margin values; STANDARD is
    # intentionally the compatibility/default profile for future resets.
    op.add_column("orcamento_versoes", sa.Column("perfil_margens", sa.String(20), nullable=False, server_default="STANDARD"))


def downgrade() -> None:
    op.drop_column("orcamento_versoes", "perfil_margens")
