"""Tabela de fornecedores, semeada a partir dos nomes que já existem.

Até aqui o fornecedor era apenas texto solto na linha da matéria-prima, sem
email nem contacto — e sem email não há pedido de preços nenhum. Esta migração
cria a tabela, semeia-a com os nomes distintos que já estão no catálogo e liga
cada matéria-prima ao seu fornecedor.

A coluna de texto ``fornecedor`` **fica**: é o que garante que nada se perde se
um nome não casar, e continua a servir de rótulo nos ecrãs antigos.

Migração aditiva. Não toca em orçamentos nem em bases externas.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260825_96"
down_revision: str | Sequence[str] | None = "20260825_95"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "def_fornecedores"
TABELA_MP = "def_materias_primas"


def _colunas(tabela: str) -> set[str]:
    return {coluna["name"] for coluna in sa.inspect(op.get_bind()).get_columns(tabela)}


def _create_index(nome: str, tabela: str, colunas: list[str]) -> None:
    indices = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes(tabela)
        if item.get("name")
    }
    if nome not in indices:
        op.create_index(nome, tabela, colunas)


def _drop_index(nome: str, tabela: str) -> None:
    indices = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes(tabela)
        if item.get("name")
    }
    if nome in indices:
        op.drop_index(nome, table_name=tabela)


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


def _semear_fornecedores() -> None:
    """Criar um fornecedor por cada nome distinto já usado no catálogo.

    Escrito em SQL portável (sem UPDATE ... JOIN) para correr igual no MySQL e
    no SQLite dos testes. Só semeia o que ainda não existe, por isso pode
    correr duas vezes.
    """
    op.execute(
        sa.text(
            f"INSERT INTO {TABELA} (nome, ativo) "
            f"SELECT DISTINCT TRIM(fornecedor), 1 FROM {TABELA_MP} "
            "WHERE fornecedor IS NOT NULL AND TRIM(fornecedor) <> '' "
            f"AND TRIM(fornecedor) NOT IN (SELECT nome FROM {TABELA})"
        )
    )
    op.execute(
        sa.text(
            f"UPDATE {TABELA_MP} SET fornecedor_id = ("
            f"  SELECT f.id FROM {TABELA} f WHERE f.nome = TRIM({TABELA_MP}.fornecedor)"
            ") WHERE fornecedor IS NOT NULL AND TRIM(fornecedor) <> ''"
        )
    )


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table(TABELA):
        op.create_table(
            TABELA,
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("nome", sa.String(150), nullable=False),
            # Sugestão de destinatário: no envio, o utilizador pode alterá-la.
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("email_cc", sa.String(255), nullable=True),
            sa.Column("pessoa_contacto", sa.String(150), nullable=True),
            sa.Column("telefone", sa.String(50), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
            ),
            sa.Column(
                "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
            ),
            sa.UniqueConstraint("nome", name="uq_def_fornecedores_nome"),
        )
        _create_index(f"ix_{TABELA}_ativo", TABELA, ["ativo"])

    if "fornecedor_id" not in _colunas(TABELA_MP):
        op.add_column(TABELA_MP, sa.Column("fornecedor_id", sa.BigInteger(), nullable=True))
    _create_index(f"ix_{TABELA_MP}_fornecedor_id", TABELA_MP, ["fornecedor_id"])

    _semear_fornecedores()
    _aplicar_grants()


def downgrade() -> None:
    _drop_index(f"ix_{TABELA_MP}_fornecedor_id", TABELA_MP)
    if "fornecedor_id" in _colunas(TABELA_MP):
        op.drop_column(TABELA_MP, "fornecedor_id")

    if sa.inspect(op.get_bind()).has_table(TABELA):
        op.drop_table(TABELA)
