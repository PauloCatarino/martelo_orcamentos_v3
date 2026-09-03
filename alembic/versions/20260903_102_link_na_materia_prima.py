"""Um link na ficha da matéria-prima.

Uma referência de catálogo (FER0016, PLC0033) não diz que aspeto tem a peça.
Quem está a orçamentar precisa muitas vezes de ver a ferragem — a página do
fabricante, a foto do fornecedor, o PDF do sistema — e hoje isso vive num
favorito do browser de cada um ou num email antigo.

Este campo é o sítio onde essa morada fica junto do material. É opcional: a
esmagadora maioria dos materiais nunca vai ter link nenhum, e não ter link não
é aviso nem erro.

Fica com 1000 caracteres porque os links dos catálogos dos fornecedores levam
muito parâmetro atrás e um `VARCHAR(255)` cortava-os a meio — um link cortado
não abre e não se percebe porquê.

Revision ID: 20260903_102
Revises: 20260901_101
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_102"
down_revision: str | Sequence[str] | None = "20260901_101"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "def_materias_primas"
COLUNA = "link"


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
    op.add_column(TABELA, sa.Column(COLUNA, sa.String(length=1000), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if not _tem_coluna(bind):
        return
    op.drop_column(TABELA, COLUNA)
