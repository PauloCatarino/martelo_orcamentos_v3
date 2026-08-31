"""Pasta dos instaladores, para o Martelo saber se há versão nova.

Até aqui não havia forma de um colega responder a "que versão é que tenho?" nem
a "já saiu uma correção?" -- e o número da versão é a única coisa que responde a
isso. O menu Ajuda passa a mostrar a versão instalada e a comparar com a que
está na pasta de onde toda a gente instala.

Esta migração só escreve a linha da pasta nas configurações. O valor por defeito
é a pasta que já existe no servidor, com o instalador lá dentro; quem quiser
muda-a em Configurações → Caminhos do Sistema, como qualquer outro caminho.

Revision ID: 20260901_101
Revises: 20260901_100
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_101"
down_revision: str | Sequence[str] | None = "20260901_100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHAVE = "pasta_instaladores"
VALOR = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos"
    r"\Instalador_Setup_Martelo"
)
DESCRICAO = (
    "Pasta do servidor onde ficam os instaladores do Martelo V3. O menu Ajuda "
    "lê os nomes dos ficheiros (Setup_Martelo_V3_x.y.z.exe) para dizer se a "
    "versão instalada é a mais recente."
)


def _tabela() -> sa.Table:
    return sa.table(
        "system_settings",
        sa.column("chave", sa.String),
        sa.column("valor", sa.String),
        sa.column("descricao", sa.String),
        sa.column("tipo", sa.String),
        sa.column("grupo", sa.String),
        sa.column("ativo", sa.Boolean),
    )


def upgrade() -> None:
    bind = op.get_bind()
    if "system_settings" not in sa.inspect(bind).get_table_names():
        return

    tabela = _tabela()
    ja_existe = bind.execute(
        sa.select(sa.func.count()).select_from(tabela).where(tabela.c.chave == CHAVE)
    ).scalar()
    if ja_existe:
        return

    op.execute(
        tabela.insert().values(
            chave=CHAVE,
            valor=VALOR,
            descricao=DESCRICAO,
            tipo="pasta",
            grupo="Geral",
            ativo=True,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "system_settings" not in sa.inspect(bind).get_table_names():
        return

    tabela = _tabela()
    op.execute(tabela.delete().where(tabela.c.chave == CHAVE))
