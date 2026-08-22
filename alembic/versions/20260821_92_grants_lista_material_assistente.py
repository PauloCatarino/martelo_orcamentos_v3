"""Atualizar os perfis MySQL para as tabelas do Assistente Lista Material."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260821_92"
down_revision: str | Sequence[str] | None = "20260821_91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplicar às tabelas novas os mesmos perfis das restantes tabelas V3."""
    connection = op.get_bind()
    if connection.dialect.name != "mysql":
        return
    exists = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.routines "
            "WHERE routine_schema = DATABASE() "
            "AND routine_name = 'martelo_aplicar_grants' "
            "AND routine_type = 'PROCEDURE'"
        )
    ).scalar_one()
    if exists:
        result = connection.execute(sa.text("CALL martelo_aplicar_grants()"))
        result.close()


def downgrade() -> None:
    # Não retirar permissões a utilizadores durante um downgrade automático.
    pass
