"""Orçamentos antigos: a pasta escolhida passa a ser a pasta-mãe das versões.

Pedido do Paulo (19-10-2026): um orçamento que vem do Martelo V2 já pode ter
as versões 01 a 05 no servidor, e o V3 registava-o sempre como versão 01,
gravando os ficheiros soltos na pasta escolhida. Os registos novos guardam a
pasta-mãe (``…/260186_INNERE``) e cada versão grava na sua subpasta
(``…/260186_INNERE/06``), como nos orçamentos normais.

Os orçamentos antigos já registados ficam como estão (decisão do Paulo):
a coluna nasce a 0 e eles continuam a gravar diretamente na pasta escolhida.

Revision ID: 20261019_119
Revises: 20261002_118
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261019_119"
down_revision: str | Sequence[str] | None = "20261002_118"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orcamentos",
        sa.Column(
            "pasta_manual_por_versao",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    # Migração aditiva: a marca diz onde estão os ficheiros de cada versão e
    # não deve ser apagada por um downgrade automático.
    pass
