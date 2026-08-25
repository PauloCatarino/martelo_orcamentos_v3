"""Matérias-primas geridas dentro do V3: campos novos e histórico de preços.

Migração aditiva. Traz para a base de dados o que até aqui só existia no Excel
(data do último preço, stock, cor, fabricante e referência PHC), marca o tipo de
preço (tabela ou livre), regista quem criou e quem alterou cada material, e cria
o histórico de preços que passa a acompanhar cada alteração.

Não altera nem apaga nenhuma coluna existente, e não toca em bases externas
(PHC, iMos ou armazém/HOMAG).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260825_95"
down_revision: str | Sequence[str] | None = "20260824_94"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "def_materias_primas"
TABELA_HISTORICO = "def_materias_primas_precos_historico"

# Preço vindo da tabela do fornecedor vs. material de preço livre, preenchido
# dentro de cada orçamento (PLACAS LIVRES, FERRAGEM LIVRE, ...).
TIPO_PRECO_TABELA = "TABELA"


def _colunas(tabela: str) -> set[str]:
    return {
        coluna["name"] for coluna in sa.inspect(op.get_bind()).get_columns(tabela)
    }


def _add_column(tabela: str, coluna: sa.Column) -> None:
    """Acrescentar uma coluna só se ainda não existir.

    O MySQL aplica DDL fora de transação: se uma execução parar a meio, as
    colunas anteriores ficam criadas e a migração pode ser retomada.
    """
    if coluna.name not in _colunas(tabela):
        op.add_column(tabela, coluna)


def _create_index(nome: str, tabela: str, colunas: list[str]) -> None:
    indices = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes(tabela)
        if item.get("name")
    }
    if nome not in indices:
        op.create_index(nome, tabela, colunas)


def _aplicar_grants() -> None:
    """Dar às contas MySQL os mesmos perfis das restantes tabelas do V3."""
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
        connection.execute(sa.text("CALL martelo_aplicar_grants()")).close()


def _normalizar_percentagens() -> None:
    """Passar as percentagens de fracção (0,2) para percentagem humana (20).

    Vinham do Excel como fracção, porque lá as colunas estavam formatadas como
    percentagem. Toda a aplicação já as lê através de
    ``normalize_percentagem_humana``, que multiplica por 100 o que estiver entre
    -1 e 1 — regra que funciona hoje mas que se enganaria no dia em que alguém
    escrevesse uma margem de 100% (guardada como 1, lida como 1%).

    Com os valores todos em percentagem humana, a leitura deixa de depender de
    adivinhar. É seguro correr duas vezes: depois de convertido, 20 já não está
    entre -1 e 1.

    Não mexe em orçamentos: as linhas de custeio guardam a sua própria cópia.
    """
    for coluna in ("desconto", "margem", "desperdicio_percentagem"):
        op.execute(
            sa.text(
                f"UPDATE {TABELA} SET {coluna} = {coluna} * 100 "
                f"WHERE {coluna} IS NOT NULL AND {coluna} <> 0 "
                f"AND {coluna} > -1 AND {coluna} < 1"
            )
        )


def upgrade() -> None:
    _add_column(TABELA, sa.Column("data_ultimo_preco", sa.Date(), nullable=True))
    _add_column(
        TABELA,
        sa.Column(
            "tipo_preco",
            sa.String(20),
            nullable=False,
            server_default=TIPO_PRECO_TABELA,
        ),
    )
    _add_column(TABELA, sa.Column("stock", sa.Boolean(), nullable=True))
    _add_column(TABELA, sa.Column("cor", sa.String(100), nullable=True))
    _add_column(TABELA, sa.Column("nome_fabricante", sa.String(150), nullable=True))
    _add_column(TABELA, sa.Column("ref_phc", sa.String(100), nullable=True))
    _add_column(TABELA, sa.Column("criado_por_id", sa.BigInteger(), nullable=True))
    _add_column(TABELA, sa.Column("alterado_por_id", sa.BigInteger(), nullable=True))

    _create_index(f"ix_{TABELA}_tipo_preco", TABELA, ["tipo_preco"])
    _create_index(f"ix_{TABELA}_data_ultimo_preco", TABELA, ["data_ultimo_preco"])

    if not sa.inspect(op.get_bind()).has_table(TABELA_HISTORICO):
        op.create_table(
            TABELA_HISTORICO,
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("materia_prima_id", sa.BigInteger(), nullable=False),
            sa.Column("ref_le", sa.String(100), nullable=True),
            sa.Column("preco_tabela", sa.Numeric(14, 4), nullable=True),
            sa.Column("desconto", sa.Numeric(8, 4), nullable=True),
            sa.Column("margem", sa.Numeric(8, 4), nullable=True),
            sa.Column("preco_liquido", sa.Numeric(14, 4), nullable=True),
            sa.Column("data_preco", sa.Date(), nullable=True),
            # EXCEL | MANUAL | FORNECEDOR
            sa.Column("origem", sa.String(30), nullable=False, server_default="MANUAL"),
            sa.Column("user_id", sa.BigInteger(), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        _create_index(
            f"ix_{TABELA_HISTORICO}_materia_prima_id",
            TABELA_HISTORICO,
            ["materia_prima_id"],
        )
        _create_index(f"ix_{TABELA_HISTORICO}_ref_le", TABELA_HISTORICO, ["ref_le"])

    _normalizar_percentagens()
    _aplicar_grants()


def _drop_index(nome: str, tabela: str) -> None:
    indices = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes(tabela)
        if item.get("name")
    }
    if nome in indices:
        op.drop_index(nome, table_name=tabela)


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table(TABELA_HISTORICO):
        op.drop_table(TABELA_HISTORICO)

    # Os índices saem antes das colunas: o MySQL faz isso sozinho, mas noutros
    # motores (e no SQLite dos testes) a coluna não sai com o índice em cima.
    _drop_index(f"ix_{TABELA}_tipo_preco", TABELA)
    _drop_index(f"ix_{TABELA}_data_ultimo_preco", TABELA)

    colunas = _colunas(TABELA)
    for nome in (
        "alterado_por_id",
        "criado_por_id",
        "ref_phc",
        "nome_fabricante",
        "cor",
        "stock",
        "tipo_preco",
        "data_ultimo_preco",
    ):
        if nome in colunas:
            op.drop_column(TABELA, nome)
