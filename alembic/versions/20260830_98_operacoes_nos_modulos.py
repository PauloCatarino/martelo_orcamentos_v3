"""Guardar as operações editadas à mão dentro do módulo.

Até aqui o módulo guardava só a ESTRUTURA das linhas — peça, medidas, fórmulas,
ValueSet, orlas. As operações não iam lá dentro: ao importar, cada linha voltava
a buscar as operações do catálogo da peça, e o trabalho de afinação feito na
linha (por exemplo, uma operação manual de recorte com o tempo de CNC acertado
para dar o preço pretendido) desaparecia sem aviso.

Esta coluna guarda, em cada linha do módulo, as operações que estavam editadas
localmente nessa linha de custeio. As linhas que não tinham edição local ficam
com a coluna a NULL e continuam a resolver as operações pelo catálogo da peça —
que é o que se quer, para continuarem a apanhar melhorias do catálogo.

Revision ID: 20260830_98
Revises: 20260828_97
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_98"
down_revision: str | Sequence[str] | None = "20260828_97"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "def_modulo_linhas"
COLUNA = "operacoes_json"


def _tem_coluna(inspector, tabela: str, coluna: str) -> bool:
    return coluna in {col["name"] for col in inspector.get_columns(tabela)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABELA not in inspector.get_table_names():
        return
    if _tem_coluna(inspector, TABELA, COLUNA):
        return

    op.add_column(
        TABELA,
        sa.Column(
            COLUNA,
            sa.Text(),
            nullable=True,
            comment=(
                "Operações editadas localmente nesta linha, guardadas com o "
                "módulo; NULL = resolver pelo catálogo da peça"
            ),
        ),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABELA not in inspector.get_table_names():
        return
    if not _tem_coluna(inspector, TABELA, COLUNA):
        return

    op.drop_column(TABELA, COLUNA)
