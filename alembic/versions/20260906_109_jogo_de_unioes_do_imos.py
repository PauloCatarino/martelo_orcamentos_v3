"""O Jogo de Uniões do iMos como quarta chave dos componentes.

O iMos não guarda só o nome de cada ferragem: guarda também o **jogo de
uniões** — o conjunto a que ela pertence. Na `IDBPURCH` é o
`CONNECTORSETNAME`, e vinha preenchido em 1031 das 1034 linhas da obra que
serviu de bancada:

    Dob_Recta_BL_75B1550_H0  = dobradiça FF00060 + calço FF00003
                               + batente FC00312 + 2 parafusos FF00030
    Pe_Axilo_H72_92_4pontear = pé + base + parafusos

É exactamente a coisa que o Martelo orça: uma dobradiça completa, um preço,
uma linha. Enquanto a ligação era feita pelo componente, o mesmo parafuso
aparecia dentro de quatro jogos e não havia forma de dizer a qual pertencia a
contagem. O jogo resolve isso de origem — cada linha do iMos traz o seu.

Uma matéria-prima pode reclamar vários jogos (os três pés AXILO valem a mesma
FER0058), mas um jogo só pode pertencer a uma — senão, ao ler uma obra, ninguém
saberia qual das duas contar. É a mesma regra que já vale para o componente
principal, e é o serviço que a faz cumprir.

Revision ID: 20260906_109
Revises: 20260904_108
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260906_109"
down_revision: str | Sequence[str] | None = "20260904_108"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "def_materias_primas_componentes"
COLUNA = "nome_jogo_imos"
INDICE = "ix_def_mp_componentes_nome_jogo_imos"


def _tem_coluna(inspector, tabela: str, coluna: str) -> bool:
    return coluna in {c["name"] for c in inspector.get_columns(tabela)}


def _tem_indice(inspector, tabela: str, indice: str) -> bool:
    return indice in {i["name"] for i in inspector.get_indexes(tabela)}


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
                sa.String(length=150),
                nullable=True,
                comment="Jogo de uniões do iMos (IDBPURCH.CONNECTORSETNAME).",
            ),
        )
    inspector = sa.inspect(connection)
    if not _tem_indice(inspector, TABELA, INDICE):
        # A importação de uma obra procura por esta coluna linha a linha.
        op.create_index(INDICE, TABELA, [COLUNA])

    # Uma coluna nova não muda os privilégios, mas o procedimento é barato e
    # garante que as contas de cada pessoa continuam em dia — foi a falta
    # disto que fez a migração 104 gravar em silêncio (ver a 105).
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
    if _tem_indice(inspector, TABELA, INDICE):
        op.drop_index(INDICE, table_name=TABELA)
    if _tem_coluna(inspector, TABELA, COLUNA):
        op.drop_column(TABELA, COLUNA)
