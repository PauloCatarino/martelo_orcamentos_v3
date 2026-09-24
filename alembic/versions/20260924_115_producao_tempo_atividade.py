"""Tempo ativo no iMos e na Lista Material, por encomenda, pessoa e dia.

Pedido do Paulo (24-09-2026): uma métrica do tempo que uma obra leva em
desenho (iMos) e na Lista Material (Excel), contando só tempo ativo. O
Martelo mede-o pela janela em primeiro plano; esta tabela guarda o acumulado.

Revision ID: 20260924_115
Revises: 20260916_114
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_115"
down_revision: str | Sequence[str] | None = "20260916_114"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "producao_tempo_atividade",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("programa", sa.String(length=10), nullable=False),
        sa.Column("nome_encomenda", sa.String(length=80), nullable=False),
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("segundos", sa.BigInteger(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "programa",
            "nome_encomenda",
            "dia",
            name="uq_prod_tempo_user_prog_enc_dia",
        ),
    )
    op.create_index(
        "ix_producao_tempo_atividade_user_id",
        "producao_tempo_atividade",
        ["user_id"],
    )
    op.create_index(
        "ix_producao_tempo_atividade_nome_encomenda",
        "producao_tempo_atividade",
        ["nome_encomenda"],
    )
    _atualizar_permissoes_mysql()


def _atualizar_permissoes_mysql() -> None:
    """Cada pessoa grava o seu tempo com a sua conta: os perfis têm de escrever."""
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
    # Migração aditiva: o tempo recolhido é informação de trabalho real e não
    # deve ser apagado por um downgrade automático.
    pass
