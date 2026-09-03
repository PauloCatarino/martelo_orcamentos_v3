"""Os componentes de uma matéria-prima composta, e o nome do artigo no iMos.

O Martelo orça uma ferragem como UM todo: a ``FER0015`` é uma dobradiça
completa, com um preço e uma linha no orçamento. O iMos exporta a mesma obra
desmontada — o copo numa linha, o calço noutra. Sem uma ponte entre os dois,
uma lista de ferragens de uma obra não pode ser avaliada aos preços do Martelo.

Duas coisas entram aqui:

- ``def_materias_primas.nome_imos`` — o nome do artigo no iMos, para os casos
  **1 para 1**: placas, orlas e ferragens simples não são compostas e não
  precisam de tabela nenhuma, basta o nome ao lado da Ref PHC que já existia;
- ``def_materias_primas_componentes`` — os filhos, para os casos compostos.
  Cada linha diz o que é, quantos entram em UM conjunto, e as três moradas por
  onde esse componente aparece nas listas do iMos.

**O preço continua no pai.** Isto é um mapa de referências, não uma segunda
maneira de calcular o preço: o custeio, o snapshot de cada linha de orçamento e
os orçamentos já feitos não mudam nada.

A regra que torna a contagem possível — uma referência só pode ser PRINCIPAL
num conjunto — é validada no serviço e não por uma restrição da base, porque
depende de três colunas ao mesmo tempo e da linha estar ativa. A mensagem que
o utilizador lê diz-lhe onde está a primeira ligação.

Revision ID: 20260903_104
Revises: 20260903_103
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_104"
down_revision: str | Sequence[str] | None = "20260903_103"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MATERIAS = "def_materias_primas"
COMPONENTES = "def_materias_primas_componentes"
COLUNA_NOME_IMOS = "nome_imos"


def _tabelas(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _colunas(bind, tabela: str) -> set[str]:
    return {coluna["name"] for coluna in sa.inspect(bind).get_columns(tabela)}


def upgrade() -> None:
    bind = op.get_bind()
    tabelas = _tabelas(bind)
    if MATERIAS not in tabelas:
        return

    if COLUNA_NOME_IMOS not in _colunas(bind, MATERIAS):
        op.add_column(
            MATERIAS, sa.Column(COLUNA_NOME_IMOS, sa.String(length=150), nullable=True)
        )
        op.create_index(
            "ix_def_materias_primas_nome_imos", MATERIAS, [COLUNA_NOME_IMOS]
        )

    if COMPONENTES in tabelas:
        return

    op.create_table(
        COMPONENTES,
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("materia_prima_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "papel",
            sa.String(length=20),
            nullable=False,
            server_default="SECUNDARIO",
        ),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column(
            "quantidade",
            sa.Numeric(precision=14, scale=4),
            nullable=False,
            server_default="1",
        ),
        sa.Column("nome_imos", sa.String(length=150), nullable=True),
        sa.Column("ref_phc", sa.String(length=100), nullable=True),
        sa.Column("ref_fornecedor_norm", sa.String(length=150), nullable=True),
        sa.Column("ref_fornecedor", sa.String(length=150), nullable=True),
        sa.Column("componente_materia_prima_id", sa.BigInteger(), nullable=True),
        sa.Column("preco_liquido", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_por_id", sa.BigInteger(), nullable=True),
        sa.Column("alterado_por_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["materia_prima_id"],
            [f"{MATERIAS}.id"],
            name="fk_def_mp_componentes_materia_prima",
        ),
        sa.ForeignKeyConstraint(
            ["componente_materia_prima_id"],
            [f"{MATERIAS}.id"],
            name="fk_def_mp_componentes_componente",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_def_mp_componentes_materia_prima_id", COMPONENTES, ["materia_prima_id"]
    )
    op.create_index("ix_def_mp_componentes_papel", COMPONENTES, ["papel"])
    op.create_index("ix_def_mp_componentes_nome_imos", COMPONENTES, ["nome_imos"])
    op.create_index("ix_def_mp_componentes_ref_phc", COMPONENTES, ["ref_phc"])
    op.create_index(
        "ix_def_mp_componentes_ref_fornecedor", COMPONENTES, ["ref_fornecedor_norm"]
    )
    op.create_index("ix_def_mp_componentes_ativo", COMPONENTES, ["ativo"])


def downgrade() -> None:
    bind = op.get_bind()
    tabelas = _tabelas(bind)

    if COMPONENTES in tabelas:
        op.drop_table(COMPONENTES)

    if MATERIAS in tabelas and COLUNA_NOME_IMOS in _colunas(bind, MATERIAS):
        try:
            op.drop_index("ix_def_materias_primas_nome_imos", table_name=MATERIAS)
        except Exception:  # noqa: BLE001 - o índice pode não existir
            pass
        op.drop_column(MATERIAS, COLUNA_NOME_IMOS)
