"""Criar acumulado de tempo ativo por versão de orçamento e utilizador."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260817_87"
down_revision: str | Sequence[str] | None = "20260816_86"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orcamento_tempo_atividade",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("orcamento_versao_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "segundos_ativos",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
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
            ["orcamento_versao_id"],
            ["orcamento_versoes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "orcamento_versao_id",
            "user_id",
            name="uq_orc_tempo_versao_user",
        ),
    )
    op.create_index(
        "ix_orc_tempo_versao_id",
        "orcamento_tempo_atividade",
        ["orcamento_versao_id"],
    )
    op.create_index(
        "ix_orc_tempo_user_id",
        "orcamento_tempo_atividade",
        ["user_id"],
    )
    _atualizar_permissoes_mysql()


def _atualizar_permissoes_mysql() -> None:
    """Make the new work table writable by the existing Martelo roles."""
    ligacao = op.get_bind()
    if ligacao.dialect.name != "mysql":
        return
    existe = ligacao.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.routines "
            "WHERE routine_schema = DATABASE() "
            "AND routine_name = 'martelo_aplicar_grants' "
            "AND routine_type = 'PROCEDURE'"
        )
    ).scalar_one()
    if existe:
        resultado = ligacao.execute(sa.text("CALL martelo_aplicar_grants()"))
        resultado.close()


def downgrade() -> None:
    # Migração aditiva: o tempo recolhido é informação de trabalho real e
    # não deve ser apagado automaticamente por um downgrade.
    pass
