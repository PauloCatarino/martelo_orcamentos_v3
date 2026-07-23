"""Add the user department and the per-user AI profile table."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260806_76"
down_revision: str | Sequence[str] | None = "20260805_75"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: users.departamento + ia_perfil_entradas.

    ``departamento`` é texto livre (o combo sugere valores mas aceita novos);
    ficar vazio mantém o comportamento atual. ``ia_perfil_entradas`` guarda o
    vocabulário e as preferências que cada utilizador escreve para o
    assistente — uma linha por expressão, sempre ligada a um utilizador.
    """
    op.add_column(
        "users",
        sa.Column("departamento", sa.String(length=64), nullable=True),
    )

    op.create_table(
        "ia_perfil_entradas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("expressao", sa.String(length=255), nullable=False),
        sa.Column("significado", sa.Text(), nullable=True),
        sa.Column("campos", sa.String(length=255), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ia_perfil_entradas_user_tipo",
        "ia_perfil_entradas",
        ["user_id", "tipo"],
    )


def downgrade() -> None:
    op.drop_index("ix_ia_perfil_entradas_user_tipo", table_name="ia_perfil_entradas")
    op.drop_table("ia_perfil_entradas")
    op.drop_column("users", "departamento")
