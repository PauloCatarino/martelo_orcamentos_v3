"""Dar histórico de partida às matérias-primas que nasceram fora da aplicação.

O histórico de preços só ganhava linhas quando o preço passava pela aplicação.
A maior parte do catálogo entrou por outro caminho (a importação inicial), e
por isso ficou sem linha nenhuma: 203 dos 333 materiais. Consequência prática,
apanhada pelo Paulo no PLC0051 — a Andreia mudou o preço a 31-08-2026 e o
separador "Histórico de preços" passou a ter UMA linha só, a nova. O preço que
lá estava antes desapareceu sem deixar rasto, e a coluna "Variação" ficou com
um travessão porque não havia com o que comparar.

Esta migração escreve, para cada material com preço e sem histórico nenhum, a
linha de partida: o preço que ele tem hoje, com a data do último preço e a
origem dos dados do próprio material. Não inventa valores nem mexe em preços —
só passa a escrito o que já estava na ficha do material.

A partir daqui o código também se defende sozinho: ao alterar um material que
ainda não tenha histórico, o serviço grava primeiro o preço antigo (ver
``DefMateriaPrimaService._registar_preco_de_partida``).

Nota honesta sobre dois materiais: o PLC0051 e o PLC0121 já foram alterados
antes disto existir. Como o preço antigo deles não está guardado em lado
nenhum da base, esta migração NÃO o pode recuperar — ficam com o histórico a
começar na alteração que levaram.

Revision ID: 20260901_100
Revises: 20260831_99
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_100"
down_revision: str | Sequence[str] | None = "20260831_99"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MATERIAIS = "def_materias_primas"
HISTORICO = "def_materias_primas_precos_historico"

OBSERVACAO = (
    "Preço de partida, recuperado da ficha do material: este material entrou "
    "no Martelo fora da aplicação e não tinha histórico nenhum."
)

#: A origem do preço só usa estas palavras; tudo o resto conta como manual.
ORIGENS_PRECO = ("EXCEL", "MANUAL", "FORNECEDOR")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())
    if not {MATERIAIS, HISTORICO} <= tabelas:
        return

    origem = sa.case(
        (
            sa.column("origem_dados").in_(ORIGENS_PRECO),
            sa.column("origem_dados"),
        ),
        else_=sa.literal("MANUAL"),
    )

    materiais = sa.table(
        MATERIAIS,
        sa.column("id", sa.BigInteger),
        sa.column("ref_le", sa.String),
        sa.column("preco_tabela", sa.Numeric),
        sa.column("desconto", sa.Numeric),
        sa.column("margem", sa.Numeric),
        sa.column("preco_liquido", sa.Numeric),
        sa.column("data_ultimo_preco", sa.Date),
        sa.column("origem_dados", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    historico = sa.table(
        HISTORICO,
        sa.column("materia_prima_id", sa.BigInteger),
        sa.column("ref_le", sa.String),
        sa.column("preco_tabela", sa.Numeric),
        sa.column("desconto", sa.Numeric),
        sa.column("margem", sa.Numeric),
        sa.column("preco_liquido", sa.Numeric),
        sa.column("data_preco", sa.Date),
        sa.column("origem", sa.String),
        sa.column("user_id", sa.BigInteger),
        sa.column("observacoes", sa.Text),
        sa.column("created_at", sa.DateTime),
    )

    ja_tem = (
        sa.select(sa.literal(1))
        .select_from(historico)
        .where(historico.c.materia_prima_id == materiais.c.id)
        .exists()
    )

    fonte = sa.select(
        materiais.c.id,
        materiais.c.ref_le,
        materiais.c.preco_tabela,
        materiais.c.desconto,
        materiais.c.margem,
        materiais.c.preco_liquido,
        materiais.c.data_ultimo_preco,
        origem,
        sa.literal(None),
        sa.literal(OBSERVACAO),
        materiais.c.created_at,
    ).where(
        sa.or_(
            materiais.c.preco_tabela.is_not(None),
            materiais.c.preco_liquido.is_not(None),
        ),
        sa.not_(ja_tem),
    )

    op.execute(
        historico.insert().from_select(
            [
                "materia_prima_id",
                "ref_le",
                "preco_tabela",
                "desconto",
                "margem",
                "preco_liquido",
                "data_preco",
                "origem",
                "user_id",
                "observacoes",
                "created_at",
            ],
            fonte,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if HISTORICO not in set(sa.inspect(bind).get_table_names()):
        return

    # Só as linhas que esta migração escreveu; o histórico normal fica intacto.
    op.execute(
        sa.text(
            f"DELETE FROM {HISTORICO} WHERE observacoes = :obs"  # noqa: S608
        ).bindparams(obs=OBSERVACAO)
    )
