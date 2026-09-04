"""O código de um módulo passa a ser único DENTRO do seu âmbito.

Até aqui o código era único na base inteira. Como o mesmo módulo costuma
existir nas duas prateleiras — uma cópia global, gerida pelo administrador, e a
cópia de quem o usa no dia-a-dia — era preciso inventar um código diferente
para o segundo. Foi assim que nasceram pares como
``1_MOD_2_PORTAS_3GVTS`` (global) e ``1_MOD_2_PORTAS_3_GVTS`` (utilizador):
o mesmo módulo, com um underscore de diferença, impossíveis de distinguir numa
lista.

Agora o código só tem de ser único dentro do âmbito, e nos módulos de
utilizador dentro de cada utilizador. Duas pessoas podem ter, cada uma, o seu
``MODULO_COZINHA``, e pode existir um global com o mesmo nome.

Nada no programa procura um módulo pelo código — a importação, a substituição e
a eliminação trabalham todas pelo ``id``, e a tabela ``orcamento_item_modulos``
nem sequer guarda referência ao catálogo. Por isso não há aqui ambiguidade
nenhuma a resolver: só se deixa de recusar o que não fazia mal.

Nota sobre o índice: em MySQL um NULL não colide com outro NULL, por isso este
índice sozinho não impede dois módulos GLOBAIS com o mesmo código (têm ambos
``user_id`` a NULL). Quem trata desse caso é o serviço, que verifica antes de
gravar — ver ``DefModuloService.criar``.

Revision ID: 20260904_108
Revises: 20260904_107
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260904_108"
down_revision: str | Sequence[str] | None = "20260904_107"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "def_modulos"
ANTIGO = "uq_def_modulos_codigo"
NOVO = "uq_def_modulos_codigo_ambito_user"
INDICE_CODIGO = "ix_def_modulos_codigo"


def _indices(bind) -> set[str]:
    inspector = sa.inspect(bind)
    if TABELA not in set(inspector.get_table_names()):
        return set()
    nomes = {indice["name"] for indice in inspector.get_indexes(TABELA)}
    nomes |= {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(TABELA)
    }
    return {nome for nome in nomes if nome}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABELA not in set(inspector.get_table_names()):
        return

    existentes = _indices(bind)
    if NOVO not in existentes:
        op.create_index(NOVO, TABELA, ["codigo", "ambito", "user_id"], unique=True)
    if ANTIGO in existentes:
        op.drop_constraint(ANTIGO, TABELA, type_="unique")
    # O código continua a ser procurado (ordenações, validações): fica indexado,
    # agora sem obrigar a ser único na base toda.
    if INDICE_CODIGO not in _indices(bind):
        op.create_index(INDICE_CODIGO, TABELA, ["codigo"])


def downgrade() -> None:
    bind = op.get_bind()
    existentes = _indices(bind)
    # Só se consegue voltar atrás se não houver códigos repetidos entretanto.
    if ANTIGO not in existentes:
        op.create_unique_constraint(ANTIGO, TABELA, ["codigo"])
    if INDICE_CODIGO in _indices(bind):
        op.drop_index(INDICE_CODIGO, table_name=TABELA)
    if NOVO in _indices(bind):
        op.drop_index(NOVO, table_name=TABELA)
