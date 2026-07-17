"""Move per-version general data (obra/descricao/localizacao/info_1/2) to the version.

Until now these fields lived only on the parent ``orcamentos`` row, so editing
one version changed them for every version. They become owned by each
``orcamento_versoes`` row; ``ref_cliente`` and the customer stay on the parent.

Additive + backfill: each existing version inherits its parent's current values,
so nothing visibly changes until a version is edited. The parent columns are
kept (legacy) and no longer read by the app for these fields.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260731_70"
down_revision: str | Sequence[str] | None = "20260730_69"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orcamento_versoes", sa.Column("obra", sa.String(255), nullable=True)
    )
    op.add_column(
        "orcamento_versoes", sa.Column("descricao", sa.Text(), nullable=True)
    )
    op.add_column(
        "orcamento_versoes", sa.Column("localizacao", sa.String(255), nullable=True)
    )
    op.add_column(
        "orcamento_versoes", sa.Column("info_1", sa.Text(), nullable=True)
    )
    op.add_column(
        "orcamento_versoes", sa.Column("info_2", sa.Text(), nullable=True)
    )

    # Backfill each version from its parent's current values. Correlated
    # subqueries work on both MySQL (app) and SQLite.
    op.get_bind().execute(
        sa.text(
            """
            UPDATE orcamento_versoes
            SET
                obra = (
                    SELECT o.obra FROM orcamentos o
                    WHERE o.id = orcamento_versoes.orcamento_id
                ),
                descricao = (
                    SELECT o.descricao FROM orcamentos o
                    WHERE o.id = orcamento_versoes.orcamento_id
                ),
                localizacao = (
                    SELECT o.localizacao FROM orcamentos o
                    WHERE o.id = orcamento_versoes.orcamento_id
                ),
                info_1 = (
                    SELECT o.info_1 FROM orcamentos o
                    WHERE o.id = orcamento_versoes.orcamento_id
                ),
                info_2 = (
                    SELECT o.info_2 FROM orcamentos o
                    WHERE o.id = orcamento_versoes.orcamento_id
                )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("orcamento_versoes", "info_2")
    op.drop_column("orcamento_versoes", "info_1")
    op.drop_column("orcamento_versoes", "localizacao")
    op.drop_column("orcamento_versoes", "descricao")
    op.drop_column("orcamento_versoes", "obra")
