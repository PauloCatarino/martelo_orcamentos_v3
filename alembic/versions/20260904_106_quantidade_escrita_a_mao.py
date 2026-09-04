"""Marcar quando a quantidade de uma linha foi escrita à mão.

Uma linha de custeio que vem de uma regra (os pés de um fundo, as dobradiças
de uma porta, as uniões de um topo) recalcula a quantidade a cada «Atualizar
Custos». Se alguém escrever ali um número à mão, a regra tem de se calar — e o
código já dizia isso ao utilizador, na coluna das observações:

    "Regra de quantidade PES_NIVELADORES: qt_und definido manualmente
     (regra ignorada)."

Só que não havia campo nenhum a guardar essa decisão: a condição olhava para o
``editado_localmente``, que quer dizer outra coisa — «o MATERIAL desta linha foi
trocado à mão». Resultado: bastava escolher outro material no dropdown
«Mat. default» para a regra da quantidade congelar em silêncio. Foi o que
aconteceu no 260881_01: um fundo de 900×600 ficou com 1 pé em vez de 6, porque
tinham trocado o pé nivelador.

Esta coluna passa a guardar a decisão a sério: fica a 1 só quando alguém edita
mesmo a quantidade de uma linha governada por uma regra.

Revision ID: 20260904_106
Revises: 20260903_105
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260904_106"
down_revision: str | Sequence[str] | None = "20260903_105"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "orcamento_item_custeio_linhas"
COLUNA = "quantidade_editada_localmente"


def _tem_coluna(bind) -> bool:
    inspector = sa.inspect(bind)
    if TABELA not in set(inspector.get_table_names()):
        return False
    return COLUNA in {coluna["name"] for coluna in inspector.get_columns(TABELA)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABELA not in set(inspector.get_table_names()):
        return
    if _tem_coluna(bind):
        return
    # Nasce a 0 em todas as linhas existentes: nenhuma quantidade antiga foi
    # deliberadamente escrita à mão — as que pareciam sê-lo eram, na verdade,
    # linhas com o material trocado.
    op.add_column(
        TABELA,
        sa.Column(
            COLUNA,
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _tem_coluna(bind):
        return
    op.drop_column(TABELA, COLUNA)
