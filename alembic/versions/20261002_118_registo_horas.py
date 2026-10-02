"""Registo de horas dentro do Martelo (folha de horas por pessoa).

Decisão do Paulo (02-10-2026): a app PHP isolada «Registo de Horas» deixa de
ser usada e o registo passa para o Martelo, com menu próprio por utilizador.
Duas tabelas: os dias (um por pessoa e dia) e os envios do mês à
contabilidade. O email da contabilidade fica nas configurações do sistema.

Revision ID: 20261002_118
Revises: 20260929_117
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261002_118"
down_revision: str | Sequence[str] | None = "20260929_117"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "registo_horas_dias",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False),
        sa.Column("entrada_min", sa.SmallInteger(), nullable=True),
        sa.Column("saida_min", sa.SmallInteger(), nullable=True),
        sa.Column("entrada2_min", sa.SmallInteger(), nullable=True),
        sa.Column("saida2_min", sa.SmallInteger(), nullable=True),
        sa.Column("desconto_almoco", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("desconto_jantar", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("acerto_min", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("horas_min", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("trabalhado_min", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("normais_min", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("extra_min", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column(
            "horas_normais_dia_min", sa.SmallInteger(), nullable=False, server_default="480"
        ),
        sa.Column("observacoes", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("origem", sa.String(length=20), nullable=False, server_default="martelo"),
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
        sa.UniqueConstraint("user_id", "data", name="uq_registo_horas_dias_user_data"),
    )
    op.create_index(
        "ix_registo_horas_dias_user_id", "registo_horas_dias", ["user_id"]
    )

    op.create_table(
        "registo_horas_envios",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("enviado_em", sa.DateTime(), nullable=False),
        sa.Column("destinatario", sa.String(length=255), nullable=False),
        sa.Column("normais_min", sa.Integer(), nullable=False),
        sa.Column("extra_min", sa.Integer(), nullable=False),
        sa.Column("dias_registados", sa.Integer(), nullable=False),
        sa.Column("ficheiro", sa.String(length=500), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_registo_horas_envios_user_mes",
        "registo_horas_envios",
        ["user_id", "ano", "mes"],
    )

    _criar_configuracao_email()
    _atualizar_permissoes_mysql()


def _criar_configuracao_email() -> None:
    system_settings = sa.table(
        "system_settings",
        sa.column("chave", sa.String),
        sa.column("valor", sa.Text),
        sa.column("descricao", sa.Text),
        sa.column("tipo", sa.String),
        sa.column("grupo", sa.String),
        sa.column("ativo", sa.Boolean),
    )
    ligacao = op.get_bind()
    chave = "registo_horas_email_contabilidade"
    existe = ligacao.execute(
        sa.select(system_settings.c.chave).where(system_settings.c.chave == chave)
    ).first()
    if existe is None:
        ligacao.execute(
            system_settings.insert().values(
                chave=chave,
                valor="financeiro@lancaencanto.pt",
                descricao="Email da contabilidade que recebe o registo de horas de cada mês",
                tipo="texto",
                grupo="Registo de Horas",
                ativo=True,
            )
        )


def _atualizar_permissoes_mysql() -> None:
    """Cada pessoa grava as suas horas com a sua conta: os perfis têm de escrever."""
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
    # Migração aditiva: as horas registadas são informação de pagamentos e não
    # devem ser apagadas por um downgrade automático.
    pass
