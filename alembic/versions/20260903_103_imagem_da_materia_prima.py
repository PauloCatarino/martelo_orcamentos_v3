"""A imagem do material na ficha da matéria-prima.

O IMOS já tem uma imagem para quase todas as ferragens: cada artigo tem um
campo «Preview Image» com o nome de um ficheiro, e os ficheiros vivem todos na
mesma pasta da biblioteca do IMOS (mais de quarenta mil). Uma referência de
catálogo não diz que peça é; a fotografia diz.

Duas coisas entram aqui:

- ``def_materias_primas.imagem_ficheiro`` — só o NOME do ficheiro
  (``HF_637.76.352_PE_AXILO_72_92.JPG``), não o caminho todo. É o que o IMOS
  guarda, e assim o dia em que a biblioteca mudar de sítio muda-se a
  configuração e não trezentas e tal fichas;
- a configuração ``pasta_imagens_imos``, que diz onde está essa pasta. Aparece
  sozinha em Configurações → Caminhos do Sistema, como qualquer outro caminho.

O campo é opcional e não ter imagem não é aviso nenhum.

Revision ID: 20260903_103
Revises: 20260903_102
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_103"
down_revision: str | Sequence[str] | None = "20260903_102"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "def_materias_primas"
COLUNA = "imagem_ficheiro"

CHAVE = "pasta_imagens_imos"
VALOR_DEFAULT = r"I:\Library\Info\BITMAPS"
DESCRICAO = "Pasta das imagens dos artigos do iMos (Preview Image)"


def _tem_coluna(bind) -> bool:
    inspector = sa.inspect(bind)
    if TABELA not in set(inspector.get_table_names()):
        return False
    return COLUNA in {coluna["name"] for coluna in inspector.get_columns(TABELA)}


def _tabela_settings():
    return sa.table(
        "system_settings",
        sa.column("chave", sa.String),
        sa.column("valor", sa.Text),
        sa.column("descricao", sa.Text),
        sa.column("tipo", sa.String),
        sa.column("grupo", sa.String),
        sa.column("ativo", sa.Boolean),
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if TABELA in tabelas and not _tem_coluna(bind):
        op.add_column(TABELA, sa.Column(COLUNA, sa.String(length=255), nullable=True))

    if "system_settings" not in tabelas:
        return

    settings = _tabela_settings()
    existe = bind.execute(
        sa.select(settings.c.chave).where(settings.c.chave == CHAVE)
    ).first()
    if existe is None:
        bind.execute(
            settings.insert().values(
                chave=CHAVE,
                valor=VALOR_DEFAULT,
                descricao=DESCRICAO,
                tipo="pasta",
                grupo="IMOS",
                ativo=True,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _tem_coluna(bind):
        op.drop_column(TABELA, COLUNA)
    # A configuração do caminho pode ter sido personalizada: fica.
