"""Add the manual folder path to budgets (legacy pre-V3 budgets)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260729_68"
down_revision: str | Sequence[str] | None = "20260728_67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: orcamentos.pasta_manual (server folder chosen by the user).

    When filled, exports write directly into this folder instead of the
    ``base/ano/{num}_{SIMPLEX}/versao`` convention.
    """
    op.add_column(
        "orcamentos",
        sa.Column("pasta_manual", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    """Remove the manual folder column."""
    op.drop_column("orcamentos", "pasta_manual")
