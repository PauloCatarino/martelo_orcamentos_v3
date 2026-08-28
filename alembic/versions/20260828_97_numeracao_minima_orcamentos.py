"""Piso da numeracao dos orcamentos: 2026 comeca no 260868.

O Martelo V3 entra ao servico com o ano a meio. Os orcamentos 260001..260867 de
2026 foram feitos no Martelo V2 -- o ultimo, o 260867, e' de 21 de agosto de
2026 -- e as pastas deles estao no servidor com propostas, PDF e desenhos de
clientes reais.

Como o V3 arranca com a tabela de orcamentos vazia, a regra normal ("o proximo
e' o maior mais um") dava 260001: o primeiro orcamento a serio escrevia dentro
da pasta de um cliente antigo, e o seguinte dentro da do outro, sem nada
avisar. Ja' aconteceu com os orcamentos de teste, que foram parar as pastas
260001..260006.

Esta migracao grava o piso nas configuracoes. Nao mexe em orcamento nenhum: e'
so' uma linha nova na system_settings.

Revision ID: 20260828_97
Revises: 20260825_96
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_97"
down_revision: str | Sequence[str] | None = "20260825_96"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHAVE = "orcamento_numero_minimo_2026"

#: O ultimo numero que o Martelo V2 usou em 2026 (confirmado na base do V2 a
#: 2026-08-28: MAX(num_orcamento) = 260867, de 21 de agosto). O V3 continua
#: dali para a frente.
PISO = "260868"

DESCRICAO = (
    "Numero a partir do qual o Martelo numera os orcamentos de 2026. "
    "Existe porque 260001..260867 sao do Martelo V2 e as pastas deles estao "
    "no servidor com trabalho real. Nao baixar este valor."
)


def upgrade() -> None:
    tabela = sa.table(
        "system_settings",
        sa.column("chave", sa.String),
        sa.column("valor", sa.Text),
        sa.column("descricao", sa.Text),
        sa.column("tipo", sa.String),
        sa.column("grupo", sa.String),
        sa.column("ativo", sa.Boolean),
    )

    ligacao = op.get_bind()
    ja_existe = ligacao.execute(
        sa.text("SELECT COUNT(*) FROM system_settings WHERE chave = :chave"),
        {"chave": CHAVE},
    ).scalar_one()

    # Se ja' la' estiver, e' porque alguem o ajustou a mao: nao se mexe.
    if ja_existe:
        return

    op.bulk_insert(
        tabela,
        [
            {
                "chave": CHAVE,
                "valor": PISO,
                "descricao": DESCRICAO,
                "tipo": "numero",
                "grupo": "Orcamentos",
                "ativo": True,
            }
        ],
    )


def downgrade() -> None:
    # Nao se desfaz. Tirar o piso poe o Martelo a numerar a partir do 260001 e
    # a escrever por cima de pastas de clientes -- exatamente o que isto veio
    # impedir. Se for mesmo preciso, apaga-se a chave a mao, a saber o que se
    # esta' a fazer.
    pass
