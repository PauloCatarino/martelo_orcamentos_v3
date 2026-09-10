"""Base dos catálogos de fornecedores (Fase 1).

As tabelas de preços dos fornecedores estavam todas dentro de um Excel
(``12_Placas_Referencias_COMPLETO.xlsx``) que a Pesquisa IA lia com openpyxl.
Isso deu o que tinha de dar: o leitor só reconhecia um cabeçalho se alguma
célula contivesse "refer", e separadores inteiros — Emuca, os três Innovus —
devolviam zero linhas em silêncio.

Esta migração cria a base onde esses catálogos vão passar a viver. Fica **ao
lado** do que existe: nasce vazia, ninguém a lê ainda, e o Excel continua a ser
a fonte da Pesquisa IA até à Fase 3.

Porquê uma base separada e não tabelas com prefixo na base dos orçamentos: os
catálogos reimportam-se dos ficheiros de origem sempre que for preciso, os
orçamentos não. Separadas, a base dos catálogos pode ser reconstruída do zero
sem pôr um orçamento em risco, e faz-se-lhe backup noutro ritmo. Nenhuma chave
estrangeira atravessa a fronteira — o fornecedor fica aqui como texto, não como
referência a ``def_fornecedores``.

**Antes de correr esta migração** é preciso criar a base e dar-lhe privilégios,
uma vez por servidor, com a conta de root::

    mysql -u root -p < deploy\\mysql_catalogos.sql

``CREATE DATABASE`` é um privilégio global: a conta de manutenção do Martelo não
o tem — e é bom que não tenha. Pela mesma razão os privilégios ficam lá e não
aqui: o procedimento ``martelo_aplicar_grants`` percorre as tabelas de
``DATABASE()`` e nunca chegaria a esta base. O ``deploy`` dá permissão ao nível
da base, o que também cobre as tabelas que as próximas migrações criarem.

Revision ID: 20260910_112
Revises: 20260908_111
Create Date: 2026-09-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db.catalogos import SCHEMA_CATALOGOS

revision: str = "20260910_112"
down_revision: str | Sequence[str] | None = "20260908_111"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def _exigir_base(connection) -> None:  # noqa: ANN001
    """Parar já, e a dizer porquê, se a base ainda não existir.

    Sem isto o erro que aparece é um ``Access denied`` a meio da primeira
    instrução — que não diz a ninguém que falta correr um ficheiro.
    """
    existe = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.schemata "
            "WHERE schema_name = :nome"
        ),
        {"nome": SCHEMA_CATALOGOS},
    ).scalar_one()
    if existe:
        return
    raise RuntimeError(
        f"A base `{SCHEMA_CATALOGOS}` não existe.\n"
        f"Criar primeiro, uma vez por servidor, com a conta de root:\n"
        f"    mysql -u root -p < deploy\\mysql_catalogos.sql\n"
        f"(CREATE DATABASE é um privilégio global — a conta de manutenção do "
        f"Martelo não o tem de propósito.)"
    )


def upgrade() -> None:
    """Criar as quatro tabelas dos catálogos."""
    connection = op.get_bind()
    if connection.dialect.name == "mysql":
        _exigir_base(connection)

    op.create_table(
        "forn_tabelas_precos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fornecedor", sa.String(length=150), nullable=False),
        sa.Column("fabricante", sa.String(length=150), nullable=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("referencia_tabela", sa.String(length=60), nullable=True),
        sa.Column("data_tabela", sa.Date(), nullable=True),
        sa.Column("ficheiro_origem", sa.String(length=400), nullable=True),
        sa.Column("ficheiro_hash", sa.String(length=64), nullable=True),
        sa.Column("moeda", sa.String(length=3), nullable=False, server_default="EUR"),
        sa.Column("unidade_preco", sa.String(length=10), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("importada_em", sa.DateTime(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_forn_tabelas_precos"),
        sa.UniqueConstraint("ficheiro_hash", name="uq_forn_tabelas_precos_hash"),
        schema=SCHEMA_CATALOGOS,
    )
    op.create_index(
        "ix_forn_tabelas_precos_fornecedor",
        "forn_tabelas_precos",
        ["fornecedor"],
        schema=SCHEMA_CATALOGOS,
    )
    op.create_index(
        "ix_forn_tabelas_precos_ativa",
        "forn_tabelas_precos",
        ["ativa"],
        schema=SCHEMA_CATALOGOS,
    )
    op.create_index(
        "ix_forn_tabelas_precos_data",
        "forn_tabelas_precos",
        ["data_tabela"],
        schema=SCHEMA_CATALOGOS,
    )

    op.create_table(
        "forn_artigos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fornecedor", sa.String(length=150), nullable=False),
        sa.Column("fabricante", sa.String(length=150), nullable=True),
        sa.Column("chave_natural", sa.String(length=300), nullable=False),
        sa.Column("referencia", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("nome_design", sa.String(length=200), nullable=True),
        sa.Column("unidade", sa.String(length=10), nullable=False, server_default="UN"),
        sa.Column("familia", sa.String(length=200), nullable=True),
        sa.Column("seccao", sa.String(length=200), nullable=True),
        sa.Column("catalogo", sa.String(length=60), nullable=True),
        sa.Column("pagina", sa.String(length=20), nullable=True),
        sa.Column("grupo", sa.String(length=80), nullable=True),
        sa.Column("substrato", sa.String(length=80), nullable=True),
        sa.Column("espessura_mm", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("acabamento", sa.String(length=60), nullable=True),
        sa.Column("formatos", sa.String(length=200), nullable=True),
        sa.Column("atributos", sa.JSON(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
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
        sa.PrimaryKeyConstraint("id", name="pk_forn_artigos"),
        sa.UniqueConstraint(
            "fornecedor", "chave_natural", name="uq_forn_artigos_chave_natural"
        ),
        schema=SCHEMA_CATALOGOS,
    )
    for indice, colunas in (
        ("ix_forn_artigos_referencia", ["referencia"]),
        ("ix_forn_artigos_fornecedor", ["fornecedor"]),
        ("ix_forn_artigos_familia", ["familia"]),
        ("ix_forn_artigos_grupo", ["grupo"]),
        ("ix_forn_artigos_substrato", ["substrato"]),
        ("ix_forn_artigos_espessura", ["espessura_mm"]),
        ("ix_forn_artigos_ativo", ["ativo"]),
    ):
        op.create_index(indice, "forn_artigos", colunas, schema=SCHEMA_CATALOGOS)

    op.create_table(
        "forn_artigos_precos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("artigo_id", sa.BigInteger(), nullable=False),
        sa.Column("tabela_preco_id", sa.BigInteger(), nullable=False),
        sa.Column("referencia", sa.String(length=120), nullable=True),
        sa.Column("valor", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("moeda", sa.String(length=3), nullable=False, server_default="EUR"),
        sa.Column("unidade", sa.String(length=10), nullable=False, server_default="UN"),
        sa.Column("desconto", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("valido_de", sa.Date(), nullable=True),
        sa.Column("valido_ate", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_forn_artigos_precos"),
        sa.ForeignKeyConstraint(
            ["artigo_id"],
            [f"{SCHEMA_CATALOGOS}.forn_artigos.id"],
            name="fk_forn_artigos_precos_artigo",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tabela_preco_id"],
            [f"{SCHEMA_CATALOGOS}.forn_tabelas_precos.id"],
            name="fk_forn_artigos_precos_tabela",
            ondelete="CASCADE",
        ),
        schema=SCHEMA_CATALOGOS,
    )
    for indice, colunas in (
        ("ix_forn_artigos_precos_artigo", ["artigo_id"]),
        ("ix_forn_artigos_precos_tabela", ["tabela_preco_id"]),
        ("ix_forn_artigos_precos_referencia", ["referencia"]),
    ):
        op.create_index(indice, "forn_artigos_precos", colunas, schema=SCHEMA_CATALOGOS)

    op.create_table(
        "forn_artigos_aliases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("artigo_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("valor", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_forn_artigos_aliases"),
        sa.ForeignKeyConstraint(
            ["artigo_id"],
            [f"{SCHEMA_CATALOGOS}.forn_artigos.id"],
            name="fk_forn_artigos_aliases_artigo",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "artigo_id", "tipo", "valor", name="uq_forn_artigos_aliases_valor"
        ),
        schema=SCHEMA_CATALOGOS,
    )
    op.create_index(
        "ix_forn_artigos_aliases_valor",
        "forn_artigos_aliases",
        ["valor"],
        schema=SCHEMA_CATALOGOS,
    )
    op.create_index(
        "ix_forn_artigos_aliases_artigo",
        "forn_artigos_aliases",
        ["artigo_id"],
        schema=SCHEMA_CATALOGOS,
    )


def downgrade() -> None:
    """Reversão automática desativada.

    Descer daqui significa apagar a base dos catálogos inteira. Isso é decisão
    do Paulo e faz-se à mão, com o comando à frente dos olhos — não por um
    ``alembic downgrade`` que corre sozinho.
    """
    raise RuntimeError(
        "Reversão automática desativada: apagar a base dos catálogos é decisão "
        "manual. Ver a docstring desta migração."
    )
