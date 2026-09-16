"""Dicionário da casa para o corretor ortográfico.

As palavras que os utilizadores acrescentam («Adicionar ao dicionário») ficam
aqui e valem para todos. A tabela nasce sem privilégios para as contas de cada
pessoa, por isso chama-se o ``martelo_aplicar_grants`` (ver migração 105) —
senão só o administrador conseguia acrescentar palavras.

Revision ID: 20260916_114
Revises: 20260912_113
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260916_114"
down_revision: str | Sequence[str] | None = "20260912_113"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "dicionario_palavras"


def upgrade() -> None:
    bind = op.get_bind()
    if TABELA not in set(sa.inspect(bind).get_table_names()):
        op.create_table(
            TABELA,
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("palavra", sa.String(length=80), nullable=False),
            sa.Column("criado_por_id", sa.BigInteger(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("palavra", name="uq_dicionario_palavras_palavra"),
        )

    if bind.dialect.name != "mysql":
        return
    existe = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.routines "
            "WHERE routine_schema = DATABASE() "
            "AND routine_name = 'martelo_aplicar_grants' "
            "AND routine_type = 'PROCEDURE'"
        )
    ).scalar_one()
    if existe:
        bind.execute(sa.text("CALL martelo_aplicar_grants()")).close()


def downgrade() -> None:
    raise RuntimeError("Reversão destrutiva exige autorização explícita do utilizador.")
