"""Manual-operation minutes per unit + service pieces (phase 8S.3 follow-up).

Adds:
- ``minutos_unitarios`` (item cost lines): minutes per unit of an OPERACAO_MANUAL
  line, so editing its quantity recomputes time and cost.
- ``sem_material`` (def_pecas): marks a service piece whose cost comes only from
  its operations (no raw material / ValueSet).
- ``sem_material`` (item cost lines): snapshot of the above on each cost line, so
  the costing can skip material/ValueSet warnings without re-resolving the piece.

Backfills existing OPERACAO_MANUAL lines so minutos_unitarios = tempo_manual /
quantidade (quantity empty/0 -> 1).

Revision ID: 20260611_27
Revises: 20260610_26
Create Date: 2026-06-11
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260611_27"
down_revision: str | Sequence[str] | None = "20260610_26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LINHAS = "orcamento_item_custeio_linhas"
_PECAS = "def_pecas"


def upgrade() -> None:
    """Add minutos_unitarios + sem_material columns and backfill manual lines."""
    op.add_column(
        _LINHAS, sa.Column("minutos_unitarios", sa.Numeric(14, 4), nullable=True)
    )
    op.add_column(
        _LINHAS,
        sa.Column(
            "sem_material",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        _PECAS,
        sa.Column(
            "sem_material",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # Derive minutos_unitarios for existing manual-operation lines.
    op.execute(
        sa.text(
            """
            UPDATE orcamento_item_custeio_linhas
            SET minutos_unitarios = tempo_manual / CASE
                WHEN quantidade IS NULL OR quantidade = 0 THEN 1
                ELSE quantidade
            END
            WHERE tipo_linha = 'OPERACAO_MANUAL'
              AND tempo_manual IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    """Drop minutos_unitarios + sem_material columns."""
    op.drop_column(_PECAS, "sem_material")
    op.drop_column(_LINHAS, "sem_material")
    op.drop_column(_LINHAS, "minutos_unitarios")
