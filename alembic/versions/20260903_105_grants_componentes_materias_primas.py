"""Dar aos perfis MySQL acesso à tabela dos componentes.

Na base de produção cada pessoa tem a sua conta, e os privilégios são dados
**tabela a tabela** através de dois perfis (``martelo_normal`` e
``martelo_admin``) — ver ``deploy/mysql_contas_beta.sql``. Uma tabela criada
por uma migração nasce sem privilégios nenhuns: existe, o administrador
escreve nela, e mais ninguém.

Foi o que aconteceu com a migração 104. O Paulo escrevia os componentes de uma
ferragem, gravava, e não ficava nada — a base recusava o INSERT à conta dele e
o Martelo, na altura, ainda mostrava esse erro por trás da ficha aberta.

O procedimento ``martelo_aplicar_grants`` percorre todas as tabelas da base e
põe as contas em dia. Chamá-lo aqui é o mesmo que a migração 92 já fazia para
as tabelas do Assistente Lista Material.

Revision ID: 20260903_105
Revises: 20260903_104
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_105"
down_revision: str | Sequence[str] | None = "20260903_104"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplicar às tabelas novas os mesmos perfis das restantes tabelas V3."""
    connection = op.get_bind()
    if connection.dialect.name != "mysql":
        return
    existe = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.routines "
            "WHERE routine_schema = DATABASE() "
            "AND routine_name = 'martelo_aplicar_grants' "
            "AND routine_type = 'PROCEDURE'"
        )
    ).scalar_one()
    if existe:
        resultado = connection.execute(sa.text("CALL martelo_aplicar_grants()"))
        resultado.close()


def downgrade() -> None:
    # Não retirar permissões a utilizadores durante um downgrade automático.
    pass
