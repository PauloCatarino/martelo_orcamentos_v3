"""Registo de horas: Teletrabalho e várias entradas e saídas no mesmo dia.

Pedido do Paulo (19-10-2026, respostas ao mockup): cada dia pode ter até 6
linhas Entrada/Saída (``periodos``, em JSON), há um tipo de dia novo
«Teletrabalho» — contado pelo relógio, com «Ausência justificada»
(``ausencia_min``) — e o que faltou para as horas normais nesse dia fica à
parte (``falta_min``), para a contabilidade ver as extra e as faltas cada uma
no seu sítio. O tipo novo cabe na coluna ``tipo`` (String 16) que já existe.

Só acrescenta colunas a uma tabela que já existe: não cria tabelas, não
precisa de ``martelo_aplicar_grants()``. Os dias já gravados ficam como estão.

Revision ID: 20261019_120
Revises: 20261019_119
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261019_120"
down_revision: str | Sequence[str] | None = "20261019_119"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("registo_horas_dias", sa.Column("periodos", sa.Text(), nullable=True))
    op.add_column(
        "registo_horas_dias",
        sa.Column("ausencia_min", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "registo_horas_dias",
        sa.Column("falta_min", sa.SmallInteger(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    # Migração aditiva: as horas registadas são informação de pagamentos e não
    # devem ser apagadas por um downgrade automático.
    pass
