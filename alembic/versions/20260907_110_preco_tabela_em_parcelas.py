"""Guardar o preço de tabela também como foi escrito: «0,25 + 0,15».

Uma ferragem é muitas vezes um conjunto de artigos com preços diferentes — o
suporte TRIS são dois (0,25 + 0,15), o pé AXILO são três. Até agora só ficava
o total, e daí a uns meses ninguém se lembra de onde veio.

A coluna guarda o texto **como o utilizador o escreveu**; o total continua no
``preco_tabela`` de sempre, e é esse que alimenta o custeio, o histórico de
preços e o snapshot de cada linha de orçamento. Nada muda nas contas: isto é
memória, não uma segunda forma de calcular.

Fica vazia quando o preço é um número só — não vale a pena guardar «0,25»
duas vezes.

Revision ID: 20260907_110
Revises: 20260906_109
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260907_110"
down_revision: str | Sequence[str] | None = "20260906_109"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "def_materias_primas"
COLUNA = "preco_tabela_parcelas"


def _tem_coluna(inspector, tabela: str, coluna: str) -> bool:
    return coluna in {c["name"] for c in inspector.get_columns(tabela)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if TABELA not in inspector.get_table_names():
        return

    if not _tem_coluna(inspector, TABELA, COLUNA):
        op.add_column(
            TABELA,
            sa.Column(
                COLUNA,
                sa.String(length=200),
                nullable=True,
                comment=(
                    "Preço de tabela como foi escrito, quando é uma soma de "
                    "parcelas. O total está em preco_tabela."
                ),
            ),
        )

    # Uma coluna nova não muda privilégios, mas o procedimento é barato e
    # mantém as contas de cada pessoa em dia (ver a migração 105).
    if connection.dialect.name == "mysql":
        existe = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM information_schema.routines "
                "WHERE routine_schema = DATABASE() "
                "AND routine_name = 'martelo_aplicar_grants' "
                "AND routine_type = 'PROCEDURE'"
            )
        ).scalar_one()
        if existe:
            connection.execute(sa.text("CALL martelo_aplicar_grants()")).close()


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if TABELA not in inspector.get_table_names():
        return
    if _tem_coluna(inspector, TABELA, COLUNA):
        op.drop_column(TABELA, COLUNA)
