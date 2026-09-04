"""A operação manual leva a máquina e os minutos dentro do módulo.

Uma linha de «Inserir operação manual» (montagem, embalamento, um recorte de
CNC) não tem peça nem operações do catálogo: o trabalho ESTÁ nos dois campos
que ela própria guarda — a máquina e os minutos por unidade. O módulo copiava a
descrição e as quantidades e deixava esses dois para trás, por isso um módulo
importado trazia a linha com 0 minutos e **0 €**.

É o pior tipo de erro: a linha aparece na tabela, com o nome certo, e quem
orçamenta assume que o tempo está contado. O Paulo apanhou um bloco de gavetas
que devia levar 50 € de montagem e levava zero.

Estas duas colunas guardam o que faltava. O custo continua a NÃO ser guardado —
é recalculado na importação com a tarifa atual da máquina, que é o que se quer.

Revision ID: 20260904_107
Revises: 20260904_106
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260904_107"
down_revision: str | Sequence[str] | None = "20260904_106"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "def_modulo_linhas"
COLUNAS = {
    "def_maquina_id": sa.Column("def_maquina_id", sa.BigInteger(), nullable=True),
    "minutos_unitarios": sa.Column(
        "minutos_unitarios", sa.Numeric(14, 4), nullable=True
    ),
}


def _colunas_existentes(bind) -> set[str]:
    inspector = sa.inspect(bind)
    if TABELA not in set(inspector.get_table_names()):
        return set()
    return {coluna["name"] for coluna in inspector.get_columns(TABELA)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABELA not in set(inspector.get_table_names()):
        return
    existentes = _colunas_existentes(bind)
    for nome, coluna in COLUNAS.items():
        if nome not in existentes:
            op.add_column(TABELA, coluna)


def downgrade() -> None:
    bind = op.get_bind()
    existentes = _colunas_existentes(bind)
    for nome in COLUNAS:
        if nome in existentes:
            op.drop_column(TABELA, nome)
