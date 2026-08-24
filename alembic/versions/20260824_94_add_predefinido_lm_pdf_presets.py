"""Adicionar preset PDF predefinido por utilizador e cliente."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260824_94"
down_revision: str | Sequence[str] | None = "20260823_93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lm_pdf_presets",
        sa.Column(
            "predefinido",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    # Preservar a configuração em vez de remover dados num downgrade automático.
    pass
