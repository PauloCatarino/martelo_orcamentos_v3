"""Add clientes.email_orcamentos / email_projeto_producao."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260811_81"
down_revision: str | Sequence[str] | None = "20260810_80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: para onde vai o orçamento e para onde vai o projeto de produção.

    O ``email`` do cliente vem do PHC e serve para tudo (muitas vezes traz
    vários endereços e o contacto da faturação). Quem envia o orçamento e quem
    envia o projeto de produção raramente escreve para o mesmo sítio, e essa
    escolha é do Martelo — não do PHC, que a sincronização voltaria a
    sobrepor.

    Ficam semeadas com o ``email`` atual do cliente para que ninguém tenha de
    reconfigurar 520 clientes à mão; a partir daí são editadas no menu Clientes.
    """
    op.add_column(
        "clientes",
        sa.Column("email_orcamentos", sa.Text(), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column("email_projeto_producao", sa.Text(), nullable=True),
    )
    op.execute(
        "UPDATE clientes SET email_orcamentos = email, "
        "email_projeto_producao = email "
        "WHERE email IS NOT NULL AND TRIM(email) <> ''"
    )


def downgrade() -> None:
    """Remove os emails de envio (o ``email`` do PHC fica como estava)."""
    op.drop_column("clientes", "email_projeto_producao")
    op.drop_column("clientes", "email_orcamentos")
