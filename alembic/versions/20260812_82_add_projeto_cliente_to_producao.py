"""Add producao.projeto_cliente_* (rasto do projeto enviado ao cliente)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260812_82"
down_revision: str | Sequence[str] | None = "20260811_81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: quando o cliente foi informado de que a obra entrou em produção.

    Ao passar uma obra para Produção, o Martelo prepara um email a avisar o
    cliente. Quem envia é o utilizador, e o que fica aqui é o rasto desse
    envio — a data que a coluna "Projeto Cliente" mostra e o detalhe da dica
    (para onde foi e quem enviou). Reenviar mais tarde atualiza estas colunas.

    Ficam a NULL nas obras existentes: os avisos que foram dados à mão até aqui
    não são conhecidos pelo Martelo.
    """
    op.add_column(
        "producao",
        sa.Column("projeto_cliente_enviado_em", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "producao",
        sa.Column("projeto_cliente_email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "producao",
        sa.Column("projeto_cliente_enviado_por_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_producao_projeto_cliente_enviado_por",
        "producao",
        "users",
        ["projeto_cliente_enviado_por_id"],
        ["id"],
    )


def downgrade() -> None:
    """Remove o rasto do projeto enviado ao cliente."""
    op.drop_constraint(
        "fk_producao_projeto_cliente_enviado_por", "producao", type_="foreignkey"
    )
    op.drop_column("producao", "projeto_cliente_enviado_por_id")
    op.drop_column("producao", "projeto_cliente_email")
    op.drop_column("producao", "projeto_cliente_enviado_em")
